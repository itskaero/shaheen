# Upstream: vGPU "holographic-card" example

Verbatim copy of the official example, kept for attribution and so later
upstream changes can be diffed. Nothing here is bundled; the adapted
renderer lives one directory up (docs/DECISIONS.md ADR-117).

- Fetched with `npx vgpu examples show|cat holographic-card` (vgpu 0.5.0;
  `examples pull` refuses to write files on Windows).
- Gallery: https://vgpu.sh — example id `holographic-card`
- Revision: `6fa27bb458ffc3f498727090f09dce3fe5faabb43689fd669d633a2a23dc36bb`
- Aggregate SHA-256: `7855eb828f858f8efc7d20805665e0b6980796d925b6af3e08b48ff52f25c144`
- License: MIT, Copyright (c) 2025 Vercel, Inc. (the `vgpu` package and its
  example gallery, https://github.com/vercel-labs/vgpu). See LICENSE.vgpu.

| File | SHA-256 |
|---|---|
| index.tsx | 6a28c33426bfbda81b66cd4b611eb632b08b898219b762b25cfa9a3a9ce44916 |
| renderer.ts | 06fdd35e03db11b936e12fa65914a1aff39fc66bdba74b15feb6bcc3d7787557 |
| scene.ts | 658116424493d99483ca2326657574ade6782ab7424395a956c67371a0623b9b |
| lettering.ts | 644a7471b8a86360a97d278e99c5d925d2db658de7ec3a2fb6a019669cb9ea7c |
| shader.wgsl | 190136f2a6a37448cf9ece1c87c552cc85516867eb896a4459f86ca65f010b39 |
