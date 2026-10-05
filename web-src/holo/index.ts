// BRAWLISTAN holographic cards: the DOM layer (docs/DECISIONS.md ADR-117).
//
// Any element marked `data-holo` becomes a card. The page writes the card's
// HTML (logo fallback, name, stats) and this module adds the WebGPU surface
// behind it, mounting and unmounting automatically as pages re-render, so
// page scripts never manage GPU lifetimes. Markup contract:
//
//   <div class="holo-card" data-holo data-holo-art="assets/img/teams/x.webp"
//        data-holo-accent="#3df26e" data-holo-accent2="#f0168c"
//        data-holo-ambient="0.3" data-holo-dpr="1.5">
//     <div class="holo-stage">
//       <canvas class="holo-canvas" aria-hidden="true"></canvas>
//       <div class="holo-face">
//         <div class="holo-fallback" aria-hidden="true">…logo img…</div>
//         <div class="holo-content">…real HTML…</div>
//       </div>
//     </div>
//   </div>
//
// Without WebGPU (or if it fails or is lost) the same card stays visible as
// its CSS fallback with a gentle CSS tilt. Nothing is shown to the visitor
// about it; details go to the console on localhost or with ?holo-debug.

import { renderer, devLog } from './renderer';
import { parseColor } from './color';
import { DEFAULT_THEME, FRAME, type Theme } from './scene';

interface Mounted {
  dispose(): void;
}

const mounted = new Map<HTMLElement, Mounted>();
const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

export function themeOf(el: HTMLElement): Theme {
  return {
    accent: parseColor(el.dataset.holoAccent, DEFAULT_THEME.accent),
    accent2: parseColor(el.dataset.holoAccent2, DEFAULT_THEME.accent2),
    cream: parseColor(el.dataset.holoCream, DEFAULT_THEME.cream),
  };
}

/** The HTML face copies the GPU card's tilt, so the text moves with the card. */
function setTilt(face: HTMLElement, tiltX: number, tiltY: number): void {
  face.style.transform =
    Math.abs(tiltX) + Math.abs(tiltY) < 1e-4 ? '' : `rotateY(${tiltX}rad) rotateX(${tiltY}rad)`;
}

/** Lightweight CSS tilt for the fallback card: no GPU, no animation loop. */
function cssTilt(el: HTMLElement, stage: HTMLElement, face: HTMLElement): () => void {
  const move = (event: PointerEvent) => {
    if (!event.isPrimary) return;
    const rect = stage.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const y = ((event.clientY - rect.top) / rect.height) * 2 - 1;
    el.style.setProperty('--holo-mx', `${(x + 1) * 50}%`);
    el.style.setProperty('--holo-my', `${(y + 1) * 50}%`);
    if (!reducedMotion()) setTilt(face, Math.max(-1, Math.min(1, x)) * 0.12, -Math.max(-1, Math.min(1, y)) * 0.09);
  };
  const leave = () => setTilt(face, 0, 0);
  stage.addEventListener('pointermove', move, { passive: true });
  stage.addEventListener('pointerleave', leave);
  return () => {
    stage.removeEventListener('pointermove', move);
    stage.removeEventListener('pointerleave', leave);
    setTilt(face, 0, 0);
  };
}

function mount(el: HTMLElement): void {
  if (mounted.has(el)) return;
  const stage = el.querySelector<HTMLElement>('.holo-stage');
  const canvas = el.querySelector<HTMLCanvasElement>('canvas.holo-canvas');
  const face = el.querySelector<HTMLElement>('.holo-face');
  if (!stage || !canvas || !face) {
    devLog('card markup incomplete', el);
    return;
  }

  let removeFallback: (() => void) | undefined;
  const showFallback = (reason: unknown) => {
    devLog('using the CSS card', reason);
    el.classList.remove('is-gpu');
    el.classList.add('is-fallback');
    removeFallback ??= cssTilt(el, stage, face);
  };

  const art = el.dataset.holoArt ? new URL(el.dataset.holoArt, document.baseURI).href : undefined;
  const dprMax = Number(el.dataset.holoDpr) || 2;
  const handle = renderer().mount({
    canvas,
    hitArea: stage,
    theme: themeOf(el),
    artUrl: art,
    ambient: Number(el.dataset.holoAmbient) || 0,
    dpr: [1, Math.max(1, Math.min(2, dprMax))],
    onTilt: (x, y) => setTilt(face, x, y),
    // Same eye distance as the shader (4.5 card units), in CSS pixels.
    onResize: (width, height) =>
      stage.style.setProperty('--holo-persp', `${(4.5 / FRAME) * Math.min(height, width * 1.35)}px`),
    onReady: () => {
      if (!el.classList.contains('is-fallback')) el.classList.add('is-gpu');
    },
    onFallback: showFallback,
  });

  mounted.set(el, {
    dispose() {
      handle.dispose();
      removeFallback?.();
    },
  });
}

function unmount(el: HTMLElement): void {
  mounted.get(el)?.dispose();
  mounted.delete(el);
}

function cardsIn(node: Node): HTMLElement[] {
  if (!(node instanceof HTMLElement)) return [];
  const found = [...node.querySelectorAll<HTMLElement>('[data-holo]')];
  return node.matches('[data-holo]') ? [node, ...found] : found;
}

/** Mount every card on the page that isn't mounted yet. */
export function refresh(): void {
  for (const el of cardsIn(document.body)) mount(el);
}

function start(): void {
  refresh();
  // Cards follow the DOM: list re-renders and removed sections clean up after themselves.
  new MutationObserver((records) => {
    for (const record of records) {
      for (const node of record.removedNodes) for (const el of cardsIn(node)) if (!el.isConnected) unmount(el);
      for (const node of record.addedNodes) for (const el of cardsIn(node)) mount(el);
    }
  }).observe(document.body, { childList: true, subtree: true });

  // Leaving the page releases the GPU; coming back from the back/forward cache re-creates it.
  addEventListener('pagehide', () => {
    for (const el of [...mounted.keys()]) unmount(el);
    renderer().disposeAll();
  });
  addEventListener('pageshow', (event) => {
    if (event.persisted) refresh();
  });
}

declare global {
  interface Window {
    BrawlistanHolo?: { refresh: () => void; stats: () => ReturnType<ReturnType<typeof renderer>['stats']> };
  }
}

window.BrawlistanHolo = { refresh, stats: () => renderer().stats() };

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
else start();
