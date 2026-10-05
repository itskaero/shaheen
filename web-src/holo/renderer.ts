// Shared WebGPU renderer for every holographic card on a page
// (docs/DECISIONS.md ADR-117).
//
// Adapted from the vGPU "holographic-card" example's renderer.ts (MIT,
// Copyright (c) 2025 Vercel, Inc.; original in ./upstream). Kept from
// upstream, unchanged in behaviour: `init` -> `surface` (dpr [1, 2]) ->
// effect compile -> `frameLoop` at 60 fps with `clock` delta timing; the
// pointer-proximity reveal, tilt and light maths and their exponential
// smoothing; reduced-motion handling; `output.onResize`; idempotent dispose
// that also covers disposal mid-initialisation.
//
// Changed so a page can carry several cards without several GPUs' worth of
// work:
//  - ONE Gpu (device) per page, shared by every card; each card is a surface.
//  - ONE frameLoop for all cards. It runs only while a card is in view and
//    still moving, and stops when everything has settled, so an idle page
//    renders nothing. Off-screen cards (IntersectionObserver) and a hidden tab
//    never render.
//  - Effects are pooled and logo textures are shared and ref-counted, so
//    re-rendering a list doesn't grow GPU memory. With no cards left for a
//    few seconds (or on pagehide) the whole Gpu is disposed.
//  - Device loss marks WebGPU unusable for the page and hands every card back
//    to its CSS fallback; nothing is shown to the visitor.

import { clock, frameLoop, init, surface, type Clock, type Effect, type FrameLoopHandle, type Gpu, type Surface, type Texture } from 'vgpu';
import { cardPointer } from './pointer';
import { FRAME, artworkTexture, blankArtwork, createScene, themeParams, type Theme } from './scene';

export interface CardOptions {
  readonly canvas: HTMLCanvasElement;
  /** Element whose pointer events drive the card (the canvas plus its HTML overlay). */
  readonly hitArea: HTMLElement;
  readonly theme: Theme;
  readonly artUrl?: string;
  /** Faint foil without a pointer, 0..1. Ignored under reduced motion. */
  readonly ambient?: number;
  readonly dpr?: readonly [number, number];
  /** Every rendered frame: the tilt the HTML overlay should copy. */
  readonly onTilt?: (tiltX: number, tiltY: number) => void;
  /** CSS size of the canvas, on mount and on every resize. */
  readonly onResize?: (cssWidth: number, cssHeight: number) => void;
  /** The first frame is on screen: hide the fallback. */
  readonly onReady?: () => void;
  /** WebGPU is unavailable or was lost: show the fallback. */
  readonly onFallback?: (reason: unknown) => void;
}

export interface CardHandle {
  dispose(): void;
}

interface Card {
  readonly options: CardOptions;
  output?: Surface;
  effect?: Effect;
  artUrl?: string;
  visible: boolean;
  dirty: boolean;
  ready: boolean;
  disposed: boolean;
  removeInput: () => void;
  // Upstream's per-card animation state.
  targetHover: number;
  pointerX: number;
  pointerY: number;
  tiltX: number;
  tiltY: number;
  hover: number;
  lightX: number;
  lightY: number;
  phase: number;
}

const IDLE_DISPOSE_MS = 4000;
const SETTLED = 1e-4;

const debug = () =>
  typeof location !== 'undefined' &&
  (/^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname) || /[?&]holo-debug\b/.test(location.search));

/** Diagnostics for developers only; visitors never see WebGPU errors. */
export function devLog(...args: unknown[]): void {
  if (debug()) console.warn('[holo]', ...args);
}

export function webgpuAvailable(): boolean {
  return typeof navigator !== 'undefined' && 'gpu' in navigator && !!navigator.gpu;
}

class SharedRenderer {
  private gpu?: Gpu;
  private gpuPromise?: Promise<Gpu>;
  private failed = false;
  private loop?: FrameLoopHandle;
  private time?: Clock;
  private readonly cards = new Set<Card>();
  private readonly effectPool: Effect[] = [];
  private readonly textures = new Map<string, { promise: Promise<Texture>; refs: number }>();
  private blank?: Texture;
  private frames = 0;
  private idleTimer?: ReturnType<typeof setTimeout>;
  private readonly motion =
    typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : undefined;
  private readonly observer =
    typeof IntersectionObserver === 'function'
      ? new IntersectionObserver((entries) => this.onIntersect(entries), { rootMargin: '120px' })
      : undefined;
  private readonly byCanvas = new WeakMap<Element, Card>();

  constructor() {
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => (document.hidden ? this.stopLoop() : this.wake()));
    }
    this.motion?.addEventListener?.('change', () => {
      for (const card of this.cards) card.dirty = true;
      this.wake();
    });
  }

  get unavailable(): boolean {
    return this.failed || !webgpuAvailable();
  }

  /** Live resource counts, for the lifecycle tests (ADR-117). */
  stats() {
    return {
      cards: this.cards.size,
      rendering: [...this.cards].filter((card) => card.visible && card.effect).length,
      pooledEffects: this.effectPool.length,
      textures: this.textures.size,
      gpu: !!this.gpu && !this.gpu.disposed,
      loop: !!this.loop,
      frames: this.frames,
    };
  }

  mount(options: CardOptions): CardHandle {
    const card: Card = {
      options, visible: !this.observer, dirty: true, ready: false, disposed: false, removeInput: () => {},
      targetHover: 0, pointerX: 0, pointerY: 0, tiltX: 0, tiltY: 0, hover: 0, lightX: 0.2, lightY: -0.25,
      phase: Math.random() * Math.PI * 2,
    };
    this.cards.add(card);
    this.byCanvas.set(options.canvas, card);
    clearTimeout(this.idleTimer);
    this.observer?.observe(options.canvas);

    if (this.unavailable) {
      options.onFallback?.(new Error('WebGPU unavailable'));
    } else {
      void this.attach(card).catch((cause: unknown) => {
        if (card.disposed) return;
        devLog('card initialisation failed', cause);
        options.onFallback?.(cause);
      });
    }
    return { dispose: () => this.unmount(card) };
  }

  /** Release everything now (pagehide). Cards mounted later start a fresh Gpu. */
  disposeAll(): void {
    for (const card of [...this.cards]) this.unmount(card);
    this.disposeGpu();
  }

  // --- GPU lifetime -----------------------------------------------------------

  private ensureGpu(): Promise<Gpu> {
    if (this.gpu) return Promise.resolve(this.gpu);
    if (!this.gpuPromise) {
      this.gpuPromise = init().then(
        (gpu) => {
          this.gpu = gpu;
          this.time = clock(gpu);
          gpu.onError((error) => devLog('gpu error', error));
          void gpu.gpu.lost.then((info) => {
            // `destroyed` is our own dispose; anything else is a real loss.
            if (info.reason === 'destroyed' || this.gpu !== gpu) return;
            devLog('device lost', info.reason, info.message);
            this.failed = true;
            const cards = [...this.cards];
            this.disposeGpu();
            for (const card of cards) {
              card.output = undefined;
              card.effect = undefined;
              card.options.onFallback?.(info);
            }
          });
          return gpu;
        },
        (error: unknown) => {
          this.failed = true;
          this.gpuPromise = undefined;
          throw error;
        },
      );
    }
    return this.gpuPromise;
  }

  private disposeGpu(): void {
    this.stopLoop();
    const gpu = this.gpu;
    this.gpu = undefined;
    this.gpuPromise = undefined;
    this.time = undefined;
    this.effectPool.length = 0;
    this.textures.clear();
    this.blank = undefined;
    // Stops the loop, then frees surfaces, textures, pipelines and the device.
    gpu?.dispose();
  }

  // --- cards --------------------------------------------------------------------

  private async attach(card: Card): Promise<void> {
    const gpu = await this.ensureGpu();
    if (card.disposed || gpu.disposed) return;
    const { canvas, theme } = card.options;

    const output = surface(gpu, canvas, {
      dpr: card.options.dpr ?? [1, 2],
      alphaMode: 'premultiplied',
      clearColor: [0, 0, 0, 0],
      label: 'holo-card',
    });
    card.output = output;
    this.blank ??= blankArtwork(gpu);

    const pooled = this.effectPool.pop();
    const effect = pooled ?? createScene(gpu, output.size, this.blank, theme);
    if (pooled) {
      effect.set({
        params: { resolution: output.size, tilt: [0, 0], pointer: [0.2, -0.25], hover: 0, ambient: 0, ...themeParams(theme) },
        artwork: this.blank,
      });
    }
    await effect.compile({ colors: [output.format] });
    if (card.disposed || gpu.disposed) {
      if (!gpu.disposed) this.effectPool.push(effect);
      return;
    }
    card.effect = effect;
    this.bindInput(card, output);
    card.options.onResize?.(output.size[0] / output.dpr, output.size[1] / output.dpr);
    card.dirty = true;
    this.wake();

    const artUrl = card.options.artUrl;
    if (artUrl) {
      try {
        const art = await this.retainTexture(gpu, artUrl);
        if (card.disposed || gpu.disposed) {
          this.releaseTexture(artUrl);
          return;
        }
        card.artUrl = artUrl;
        effect.set({ artwork: art });
        card.dirty = true;
        this.wake();
      } catch (cause) {
        devLog('artwork failed to load', artUrl, cause); // the card still renders, without its logo
      }
    }
  }

  private bindInput(card: Card, output: Surface): void {
    const { canvas, hitArea } = card.options;
    const move = (event: PointerEvent) => {
      if (!event.isPrimary) return;
      // Upstream's pointer maths (pointer.ts), with the framing constant shared with the shader.
      Object.assign(card, cardPointer(canvas.getBoundingClientRect(), event.clientX, event.clientY, FRAME));
      this.wake();
    };
    const leave = () => {
      card.targetHover = 0;
      this.wake();
    };
    const up = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse') leave();
    };
    // Keyboard focus lights the card the way a pointer would.
    const focus = () => {
      card.targetHover = 0.6;
      card.pointerX = 0.15;
      card.pointerY = -0.35;
      this.wake();
    };
    hitArea.addEventListener('pointermove', move, { passive: true });
    hitArea.addEventListener('pointerdown', move, { passive: true });
    hitArea.addEventListener('pointerleave', leave);
    hitArea.addEventListener('pointercancel', leave);
    hitArea.addEventListener('pointerup', up);
    hitArea.addEventListener('focusin', focus);
    hitArea.addEventListener('focusout', leave);
    const unsubscribeResize = output.onResize((event) => {
      card.effect?.set({ params: { resolution: output.size } });
      card.options.onResize?.(event.width / event.dpr, event.height / event.dpr);
      card.dirty = true;
      this.wake();
    });
    card.removeInput = () => {
      hitArea.removeEventListener('pointermove', move);
      hitArea.removeEventListener('pointerdown', move);
      hitArea.removeEventListener('pointerleave', leave);
      hitArea.removeEventListener('pointercancel', leave);
      hitArea.removeEventListener('pointerup', up);
      hitArea.removeEventListener('focusin', focus);
      hitArea.removeEventListener('focusout', leave);
      unsubscribeResize();
    };
  }

  private unmount(card: Card): void {
    if (card.disposed) return;
    card.disposed = true;
    card.removeInput();
    this.observer?.unobserve(card.options.canvas);
    this.cards.delete(card);
    if (card.effect && this.gpu && !this.gpu.disposed) this.effectPool.push(card.effect);
    card.effect = undefined;
    card.output?.dispose();
    card.output = undefined;
    if (card.artUrl) this.releaseTexture(card.artUrl);
    card.artUrl = undefined;
    if (!this.cards.size) {
      this.stopLoop();
      clearTimeout(this.idleTimer);
      this.idleTimer = setTimeout(() => {
        if (!this.cards.size) this.disposeGpu();
      }, IDLE_DISPOSE_MS);
    }
  }

  // --- shared logo textures ---------------------------------------------------

  private retainTexture(gpu: Gpu, url: string): Promise<Texture> {
    let entry = this.textures.get(url);
    if (!entry) {
      const promise = fetch(url, { credentials: 'same-origin' })
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.blob();
        })
        .then((blob) => createImageBitmap(blob, { premultiplyAlpha: 'none', colorSpaceConversion: 'default' }))
        .then((bitmap) => {
          try {
            return artworkTexture(gpu, bitmap, `holo-artwork:${url}`);
          } finally {
            bitmap.close();
          }
        });
      entry = { promise, refs: 0 };
      this.textures.set(url, entry);
      promise.catch(() => this.textures.delete(url));
    }
    entry.refs += 1;
    return entry.promise;
  }

  private releaseTexture(url: string): void {
    const entry = this.textures.get(url);
    if (!entry) return;
    entry.refs -= 1;
    if (entry.refs > 0) return;
    this.textures.delete(url);
    // Pooled effects may still reference it; point them back at the blank texture first.
    void entry.promise.then((art) => {
      if (this.blank) for (const effect of this.effectPool) effect.set({ artwork: this.blank });
      art.destroy();
    }, () => {});
  }

  // --- visibility and the frame loop --------------------------------------------

  private onIntersect(entries: IntersectionObserverEntry[]): void {
    for (const entry of entries) {
      const card = this.byCanvas.get(entry.target);
      if (!card) continue;
      card.visible = entry.isIntersecting;
      if (card.visible) card.dirty = true;
    }
    this.wake();
  }

  private wake(): void {
    if (this.loop || !this.gpu || this.gpu.disposed || document.hidden) return;
    if (![...this.cards].some((card) => card.visible && card.effect)) return;
    const gpu = this.gpu;
    this.loop = frameLoop(gpu, (currentFrame) => {
      const reduced = this.motion?.matches ?? false;
      const dt = Math.min(this.time?.deltaTime ?? 1 / 60, 0.1);
      const now = this.time?.time ?? performance.now() / 1000;
      let busy = false;
      for (const card of this.cards) {
        if (!card.visible || !card.effect || !card.output || card.disposed) continue;
        const moving = this.step(card, dt, now, reduced);
        if (!moving && !card.dirty) continue;
        card.dirty = false;
        busy ||= moving;
        currentFrame.pass(card.output, card.effect);
        card.options.onTilt?.(card.tiltX, card.tiltY);
        if (!card.ready) {
          card.ready = true;
          // After this frame is presented.
          requestAnimationFrame(() => card.options.onReady?.());
        }
      }
      this.frames += 1;
      if (!busy) this.stopLoop();
    }, { fps: 60 });
  }

  private stopLoop(): void {
    this.loop?.stop();
    this.loop = undefined;
  }

  /** Upstream's smoothing, plus a slow ambient drift. Returns whether the card is still moving. */
  private step(card: Card, dt: number, now: number, reduced: boolean): boolean {
    const targetX = reduced ? 0 : Math.max(-1, Math.min(1, card.pointerX)) * 0.16 * card.targetHover;
    const targetY = reduced ? 0 : -Math.max(-1, Math.min(1, card.pointerY)) * 0.12 * card.targetHover;
    const blend = reduced ? 1 : 1 - Math.exp(-10 * dt);
    const before = card.tiltX + card.tiltY + card.hover + card.lightX + card.lightY;
    card.tiltX += (targetX - card.tiltX) * blend;
    card.tiltY += (targetY - card.tiltY) * blend;
    card.hover += (card.targetHover - card.hover) * blend;
    const ambient = reduced ? (card.options.ambient ?? 0) * 0.6 : (card.options.ambient ?? 0);
    const drifting = !reduced && ambient > 0 && card.targetHover < 0.05;
    if (card.targetHover > 0) {
      card.lightX += (card.pointerX - card.lightX) * blend;
      card.lightY += (card.pointerY - card.lightY) * blend;
    } else if (drifting) {
      // A light that slowly wanders across the card, so the foil breathes.
      const driftX = Math.sin(now * 0.32 + card.phase) * 0.75;
      const driftY = -0.25 + Math.sin(now * 0.23 + card.phase * 1.7) * 0.45;
      card.lightX += (driftX - card.lightX) * Math.min(1, dt * 2);
      card.lightY += (driftY - card.lightY) * Math.min(1, dt * 2);
    }
    card.effect?.set({
      params: { tilt: [card.tiltX, card.tiltY], pointer: [card.lightX, card.lightY], hover: card.hover, ambient },
    });
    const after = card.tiltX + card.tiltY + card.hover + card.lightX + card.lightY;
    return drifting || Math.abs(after - before) > SETTLED;
  }
}

let shared: SharedRenderer | undefined;

export function renderer(): SharedRenderer {
  shared ??= new SharedRenderer();
  return shared;
}
