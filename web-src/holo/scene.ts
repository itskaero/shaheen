// The card's effect (docs/DECISIONS.md ADR-117), adapted from the vGPU
// "holographic-card" example's scene.ts (MIT, Copyright (c) 2025 Vercel, Inc.;
// original in ./upstream). Upstream uploads a baked single-channel lettering
// mask; BRAWLISTAN uploads the team's logo as a premultiplied RGBA texture
// instead, because every word on the card is real HTML.

import { effect, sampler, texture, type Effect, type Gpu, type Texture } from 'vgpu';
import fragment from './shader.wgsl';

import type { Rgb } from './color';

export type { Rgb };

export interface Theme {
  readonly accent: Rgb;
  readonly accent2: Rgb;
  readonly cream: Rgb;
}

/** Card framing: canvas units per card unit (upstream used 2.5). Shared with the pointer maths. */
export const FRAME = 2.1;

export const DEFAULT_THEME: Theme = {
  accent: [0.239, 0.949, 0.431], // #3df26e
  accent2: [0.941, 0.086, 0.549], // #f0168c
  cream: [0.984, 0.976, 0.847], // #fbf9d8
};

const vec4 = (c: Rgb) => [c[0], c[1], c[2], 1] as const;

export function themeParams(theme: Theme) {
  return { accent: vec4(theme.accent), accent2: vec4(theme.accent2), cream: vec4(theme.cream) };
}

/** A transparent 1x1 texture for a card whose logo hasn't loaded (or has none). */
export function blankArtwork(gpu: Gpu): Texture {
  const blank = texture(gpu, {
    kind: '2d', size: [1, 1], format: 'rgba8unorm',
    usage: ['texture_binding', 'copy_dst'], label: 'holo-artwork-blank',
  });
  gpu.gpu.queue.writeTexture({ texture: blank.gpu }, new Uint8Array(4), { bytesPerRow: 4 }, [1, 1, 1]);
  return blank;
}

/** Uploads a decoded logo as premultiplied RGBA, the way the shader composites it. */
export function artworkTexture(gpu: Gpu, image: ImageBitmap, label: string): Texture {
  const art = texture(gpu, {
    kind: '2d', size: [image.width, image.height], format: 'rgba8unorm',
    // copyExternalImageToTexture needs render_attachment as well as copy_dst.
    usage: ['texture_binding', 'copy_dst', 'render_attachment'], label,
  });
  gpu.gpu.queue.copyExternalImageToTexture(
    { source: image },
    { texture: art.gpu, premultipliedAlpha: true },
    [image.width, image.height],
  );
  return art;
}

export function createScene(gpu: Gpu, resolution: readonly [number, number], artwork: Texture, theme: Theme): Effect {
  return effect(gpu, fragment, {
    label: 'brawlistan-holographic-card',
    set: {
      params: {
        resolution, tilt: [0, 0], pointer: [0.2, -0.25], hover: 0, ambient: 0, frame: FRAME,
        ...themeParams(theme),
      },
      artwork,
      linear: sampler(gpu, { minFilter: 'linear', magFilter: 'linear' }),
    },
  });
}
