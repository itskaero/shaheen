// BRAWLISTAN holographic card (docs/DECISIONS.md ADR-117).
//
// Adapted from the vGPU "holographic-card" example (MIT, Copyright (c) 2025
// Vercel, Inc.; verbatim original in ./upstream/shader.wgsl). The optics are
// unchanged: perspective tilt, wavy foil engraving, triangular fractal, Stam's
// diffraction-order grating, pearlescent wash, sweeping light band, glint and
// sparkle, registration ticks, rim light. What changed, and why:
//  - `artwork` (a premultiplied RGBA logo) replaces the baked demo lettering:
//    all typography is real HTML laid over the card (ADR-117).
//  - `accent`, `accent2`, `cream` tint the pearlescence and the graphite so
//    each team keeps its own colours; the shader itself is shared.
//  - `frame` (2.5 upstream) frames the card a little tighter in its canvas.
//  - `ambient` keeps a faint foil visible without a pointer.
//  - The backdrop is transparent (alpha = card + soft shadow), so the card
//    floats on the page instead of sitting on an opaque rectangle.
//  - The foil is calmer over the lower text panel, so the HTML stays legible.

struct Params {
  resolution: vec2f,
  tilt: vec2f,
  pointer: vec2f,
  hover: f32,
  ambient: f32,
  frame: f32,
  accent: vec4f,
  accent2: vec4f,
  cream: vec4f,
}
@group(0) @binding(0) var<uniform> params: Params;
@group(0) @binding(1) var artwork: texture_2d<f32>;
@group(0) @binding(2) var linear: sampler;

// The logo's square, in card units (the card is 1.28 x 1.82, centred).
const ART_CENTER = vec2f(0.0, -0.33);
const ART_SIZE = 0.92;

fn roundedBox(p: vec2f, halfSize: vec2f, radius: f32) -> f32 {
  let q = abs(p) - halfSize + radius;
  return length(max(q, vec2f(0))) + min(max(q.x, q.y), 0.0) - radius;
}

fn segment(p: vec2f, a: vec2f, b: vec2f) -> f32 {
  let v = b - a;
  return length(p - a - v * clamp(dot(p - a, v) / dot(v, v), 0.0, 1.0));
}

fn stroke(distance: f32, width: f32, aa: f32) -> f32 {
  return 1.0 - smoothstep(width, width + aa, abs(distance));
}

// Approximate visible wavelengths in micrometers with smooth display RGB responses.
fn wavelengthColor(wavelength: f32) -> vec3f {
  let response = (vec3f(wavelength) - vec3f(0.610, 0.545, 0.460)) / vec3f(0.045, 0.038, 0.032);
  let visible = smoothstep(0.380, 0.410, wavelength) * (1.0 - smoothstep(0.700, 0.780, wavelength));
  return exp(-0.5 * response * response) * visible;
}

// Reflection grating approximation: m * wavelength = d * dot(L + V, across).
// L and V point away from the surface; across is perpendicular to the grooves.
// Based on the diffraction-order model in GPU Gems, chapter 8 (Jos Stam).
fn diffraction(across: vec2f, lightAndView: vec2f, spacing: f32) -> vec3f {
  let pathDifference = spacing * abs(dot(lightAndView, across));
  let along = dot(lightAndView, vec2f(-across.y, across.x));
  // Finite, imperfect groove patches broaden the directional reflection.
  let envelope = exp(-along * along / 0.36);
  var reflected = vec3f(0);
  for (var order = 1; order <= 3; order++) {
    let m = f32(order);
    reflected += wavelengthColor(pathDifference / m) / (m * m);
  }
  return reflected * envelope;
}

// Broad, art-directed pearlescence underneath the finer diffraction detail.
fn pearlColor(phase: f32) -> vec3f {
  return vec3f(0.55, 0.52, 0.64) + vec3f(0.43, 0.40, 0.34)
    * cos(6.2831853 * (phase + vec3f(0.05, 0.38, 0.63)));
}

// The team's own pearl: the upstream pearl pulled toward a smooth cycle
// through accent -> accent2 -> cream, so SHAHEEN shimmers emerald/magenta
// and Delight cyan/violet while the physical diffraction stays spectral.
fn themedPearl(phase: f32) -> vec3f {
  let t = fract(phase);
  let a = params.accent.rgb;
  let b = params.accent2.rgb;
  let c = params.cream.rgb;
  let w0 = 0.5 + 0.5 * cos(6.2831853 * t);
  let w1 = 0.5 + 0.5 * cos(6.2831853 * (t - 0.3333));
  let w2 = 0.5 + 0.5 * cos(6.2831853 * (t - 0.6667));
  let theme = (a * w0 + b * w1 + c * w2 * 0.7) / max(w0 + w1 + w2 * 0.7, 0.001);
  return mix(pearlColor(phase), theme * 1.05, 0.62);
}

fn grain(point: vec2f) -> f32 {
  let p = vec2u(abs(point) * 2400.0);
  var n = (p.x * 1597334677u) ^ (p.y * 3812015801u);
  n = (n ^ (n >> 16u)) * 2246822519u;
  return f32(n & 1023u) / 1023.0 - 0.5;
}

fn etchedPhase(p: vec2f) -> f32 {
  // Warp the surface before tracing contours, so their spacing flows in soft waves.
  let warp = vec2f(
    sin(p.y * 7.0 + sin(p.x * 4.0)) * 0.085,
    sin(p.x * 6.0 - p.y * 3.0) * 0.07
  );
  let q = p + warp - vec2f(0.13, 0.08);
  let radius = length(q * vec2f(1.0, 0.76));
  return radius * 142.0 + sin(atan2(q.y, q.x) * 3.0 + radius * 8.0) * 1.7;
}

// Signed edge distance inside an equilateral triangle centered at its centroid.
fn triangleBoundary(p: vec2f, height: f32) -> f32 {
  return max((abs(p.x) * sqrt(3.0) - p.y - height * (2.0 / 3.0)) * 0.5, p.y - height / 3.0);
}

fn triangleGrooves(edgeDistances: vec3f) -> vec2f {
  if (edgeDistances.x <= edgeDistances.y && edgeDistances.x <= edgeDistances.z) {
    return vec2f(0, -1);
  }
  if (edgeDistances.y <= edgeDistances.z) {
    return vec2f(-sqrt(3.0) * 0.5, 0.5);
  }
  return vec2f(sqrt(3.0) * 0.5, 0.5);
}

struct FractalMark {
  coverage: f32,
  across: vec2f,
}

// Recursive triangular engraving, with screen-space antialiasing at every scale.
fn fractalEngraving(p: vec2f, halfWidth: f32, height: f32, aa: f32) -> FractalMark {
  let apex = (height / 3.0 - p.y) / height;
  var barycentric = vec3f(apex, (1.0 - apex - p.x / halfWidth) * 0.5, (1.0 - apex + p.x / halfWidth) * 0.5);
  var cellHeight = height;
  for (var level = 0; level < 6; level++) {
    let largest = max(barycentric.x, max(barycentric.y, barycentric.z));
    if (largest < 0.5) {
      // Each removed central triangle leaves a fine foil border.
      return FractalMark(stroke((0.5 - largest) * cellHeight, 0.0008, aa * 0.65), triangleGrooves(0.5 - barycentric));
    }
    var corner = vec3f(0, 0, 1);
    if (barycentric.x >= barycentric.y && barycentric.x >= barycentric.z) {
      corner = vec3f(1, 0, 0);
    } else if (barycentric.y >= barycentric.z) {
      corner = vec3f(0, 1, 0);
    }
    barycentric = barycentric * 2.0 - corner;
    cellHeight *= 0.5;
  }
  let leafEdge = min(barycentric.x, min(barycentric.y, barycentric.z)) * cellHeight;
  return FractalMark(stroke(leafEdge, 0.0006, aa * 0.5) * 0.65, triangleGrooves(barycentric));
}

@fragment
fn fs_main(@location(0) uv: vec2f) -> @location(0) vec4f {
  let resolution = max(params.resolution, vec2f(1));
  let scale = min(resolution.y, resolution.x * 1.35);
  let screen = (uv - 0.5) * resolution / scale * params.frame;
  let sx = sin(params.tilt.y);
  let cx = cos(params.tilt.y);
  let sy = sin(params.tilt.x);
  let cy = cos(params.tilt.x);
  let right = vec3f(cy, 0, -sy);
  let down = vec3f(sy * sx, cx, cy * sx);
  let normal = cross(right, down);
  let eye = vec3f(0, 0, 4.5);
  let ray = normalize(vec3f(screen, -4.5));
  let hit = eye - ray * (dot(eye, normal) / dot(ray, normal));
  let p = vec2f(dot(hit, right), dot(hit, down));
  let aa = max(length(fwidth(p)), 0.0006);
  let edge = roundedBox(p, vec2f(0.64, 0.91), 0.055);
  let silhouette = 1.0 - smoothstep(-aa, aa, edge);

  // Transparent backdrop: only the card and its soft shadow are drawn.
  let shadow = exp(-max(roundedBox(screen - vec2f(0.025, 0.06), vec2f(0.63, 0.9), 0.055), 0.0) * 22.0);

  // The lower panel carries HTML text; the foil stays quieter there.
  let textPanel = smoothstep(0.10, 0.24, p.y);
  let calm = mix(1.0, 0.42, textPanel);

  // Matte graphite remains dark; the cursor's grazing light (and a faint
  // ambient sheen) reveals the foil.
  let hover = clamp(max(params.hover, params.ambient), 0.0, 1.0);
  let lightCenter = params.pointer * vec2f(0.64, 0.91);
  let delta = p - lightCenter;
  let sweepDistance = delta.x * 0.72 + delta.y * 0.52 + sin(p.y * 4.0 + p.x * 3.0) * 0.08;
  let bandDistance = sweepDistance / 0.36;
  let lightBand = exp(-bandDistance * bandDistance);
  let glintDistance = sweepDistance / 0.085;
  let glint = exp(-glintDistance * glintDistance);
  let spotlight = exp(-dot(delta * vec2f(1.05, 0.72), delta * vec2f(1.05, 0.72)) * 2.6);
  let light = lightBand * spotlight * hover * calm;
  let lightDirection = normalize(vec3f(lightCenter, 1.2) - hit);
  let viewDirection = normalize(eye - hit);
  let lightAndView = vec2f(dot(lightDirection + viewDirection, right), dot(lightDirection + viewDirection, down));
  let illumination = max(dot(normal, lightDirection), 0.0) * max(dot(normal, viewDirection), 0.0);
  let tint = mix(vec3f(0.72, 0.76, 0.8), params.cream.rgb, 0.45);
  let noise = grain(p + vec2f(2));
  var color = mix(vec3f(0.050, 0.056, 0.060), params.accent.rgb * 0.07, 0.35) + 0.008 * (0.9 - p.y);
  // A whisper of the team colour in the graphite, strongest at the top.
  color += params.accent2.rgb * 0.018 * (1.0 - textPanel);
  // Fine, surface-locked grain catches the grazing reflection without animated static.
  color += noise * (0.022 + light * 0.085);
  color += light * (vec3f(0.045) + tint * 0.065);

  // The triangle and its fractal sit behind the logo, centred on it.
  let tp = p - ART_CENTER;
  let halfWidth = 0.46;
  let triangleHeight = halfWidth * sqrt(3.0);
  let top = vec2f(0, -triangleHeight * (2.0 / 3.0));
  let left = vec2f(-halfWidth, triangleHeight / 3.0);
  let rightCorner = vec2f(halfWidth, triangleHeight / 3.0);
  let triangleDistance = min(segment(tp, top, left), min(segment(tp, left, rightCorner), segment(tp, rightCorner, top)));
  let innerBoundary = triangleBoundary(tp, triangleHeight);
  let outerScale = 1.12;
  let outerBoundary = triangleBoundary(tp, triangleHeight * outerScale);
  let inside = 1.0 - smoothstep(-aa * 1.5, -aa * 0.5, innerBoundary);
  let outside = smoothstep(aa * 0.5, aa * 1.5, outerBoundary);

  // Separate engravings leave a clear graphite gap between the two outlines.
  let contour = etchedPhase(p);
  // Transform screen derivatives back into the card plane: microscopic grooves
  // follow the visible contours, but their 1.65um spacing is independent of zoom.
  let dx = dpdx(p);
  let dy = dpdy(p);
  let gradient = vec2f(dpdx(contour) * dy.y - dpdy(contour) * dx.y, dpdy(contour) * dx.x - dpdx(contour) * dy.x);
  let across = gradient / max(length(gradient), 0.00000001);
  let outerDiffraction = diffraction(across, lightAndView, 1.65) * illumination;
  let contours = stroke(sin(contour), 0.06, min(fwidth(contour), 1.0));
  let reveal = hover * (0.06 + 0.24 * spotlight + light * 1.15) * calm;
  let fractal = fractalEngraving(tp, halfWidth, triangleHeight, aa);
  let innerDiffraction = diffraction(fractal.across, lightAndView, 1.35) * illumination;
  let pearlPhase = dot(lightAndView, vec2f(0.48, -0.32)) + p.y * 0.32 + contour * 0.003;
  let outerPearl = themedPearl(pearlPhase);
  let innerPearl = themedPearl(pearlPhase + dot(fractal.across, lightAndView) * 0.32 + 0.12);
  // Color washes over the material between etched lines, with a narrower silver
  // flash moving through it. Both layers respect the empty gap between outlines.
  let pearl = outerPearl * outside + innerPearl * inside;
  color += pearl * light * 0.24;
  color += (pearl * 0.5 + vec3f(0.5) * (inside + outside)) * glint * spotlight * hover * calm * 0.12;
  let sparkle = pow(max(noise + 0.5, 0.0), 24.0) * glint * spotlight * hover * calm;
  color += pearl * sparkle * 0.22;
  let outerFoil = vec3f(0.12, 0.14, 0.18) + outerPearl * 0.65 + outerDiffraction * 0.12;
  let innerFoil = vec3f(0.12, 0.14, 0.18) + innerPearl * 0.65 + innerDiffraction * 0.12;
  color += (contours * 0.65 * outside * outerFoil + fractal.coverage * inside * innerFoil) * reveal;

  // A delicate spectral echo stays clipped to the same engraving regions.
  let foilOffset = vec2f(0.007, -0.004) + params.tilt * 0.012;
  let foilPoint = p - foilOffset;
  let foilPhase = etchedPhase(foilPoint);
  let foilLines = stroke(sin(foilPhase), 0.025, min(fwidth(foilPhase), 1.0));
  let foilFractal = fractalEngraving(foilPoint - ART_CENTER, halfWidth, triangleHeight, aa);
  let echoDiffraction = diffraction(foilFractal.across, lightAndView, 1.35) * illumination;
  color += (foilLines * 0.65 * outside * (outerPearl + outerDiffraction * 0.2)
    + foilFractal.coverage * inside * (innerPearl + echoDiffraction * 0.2)) * reveal * 0.22;
  // Scale every vertex around the shared centroid, keeping the outer foil centered.
  let foilEdge = min(segment(tp, top * outerScale, left * outerScale), min(segment(tp, left * outerScale, rightCorner * outerScale), segment(tp, rightCorner * outerScale, top * outerScale)));
  let foilAcross = triangleGrooves(vec3f(triangleHeight * outerScale / 3.0 - tp.y,
    (tp.y + triangleHeight * outerScale * (2.0 / 3.0) - tp.x * sqrt(3.0)) * 0.5,
    (tp.y + triangleHeight * outerScale * (2.0 / 3.0) + tp.x * sqrt(3.0)) * 0.5));
  let foilTint = outerPearl * 0.8 + vec3f(0.2) + diffraction(foilAcross, lightAndView, 1.65) * illumination * 0.15;
  color += stroke(foilEdge, 0.0007, aa * 0.5) * foilTint * hover * (0.12 + light * 0.5);

  // Sparse microdots and registration ticks emerge in the surrounding foil.
  let grid = (fract((p + 1.0) * 20.0) - 0.5) / 20.0;
  let dots = stroke(length(grid), 0.0008, aa * 0.4);
  color += dots * outside * reveal * 0.17;
  let guide = abs(p) - vec2f(0.49, 0.37);
  let horizontal = stroke(guide.y, 0.0006, aa * 0.5) * (1.0 - smoothstep(0.012, 0.017, abs(guide.x)));
  let vertical = stroke(guide.x, 0.0006, aa * 0.5) * (1.0 - smoothstep(0.012, 0.017, abs(guide.y)));
  color += max(horizontal, vertical) * hover * (0.12 + light * 0.22);

  // Always-visible outline: its baseline contrast does not depend on hover or light.
  let outline = stroke(triangleDistance, 0.0012, aa * 0.65);
  color = mix(color, mix(vec3f(0.29, 0.32, 0.36), params.accent.rgb * 0.55, 0.35) + tint * light * 0.16, outline);

  // The logo floats above the foil: a small tilt parallax, then a holographic
  // sheen over its bright areas as the light sweeps across.
  let artPoint = p - ART_CENTER + params.tilt * vec2f(0.035, -0.035);
  let artUv = artPoint / ART_SIZE + 0.5;
  let inArt = step(0.0, artUv.x) * step(artUv.x, 1.0) * step(0.0, artUv.y) * step(artUv.y, 1.0);
  let art = textureSampleLevel(artwork, linear, clamp(artUv, vec2f(0), vec2f(1)), 0.0) * inArt;
  let artLuma = dot(art.rgb, vec3f(0.299, 0.587, 0.114));
  let artSheen = (pearl * 0.5 + outerPearl * 0.5) * artLuma * (light * 0.55 + glint * spotlight * hover * 0.25);
  color = color * (1.0 - art.a) + art.rgb + artSheen;

  let mark = p - vec2f(0.505, -0.765);
  let crossMark = min(segment(mark, vec2f(-0.024, 0), vec2f(0.024, 0)), segment(mark, vec2f(0, -0.024), vec2f(0, 0.024)));
  color = mix(color, vec3f(0.48, 0.51, 0.55), stroke(crossMark, 0.0007, aa * 0.65));

  let rim = stroke(edge + 0.002, 0.0008, aa * 0.7);
  let rimLight = pow(max(0.0, 1.0 - length(delta) * 0.65), 3.0) * hover;
  color = mix(color, vec3f(0.25, 0.28, 0.32) + (outerPearl * 0.7 + tint * 0.3) * rimLight * 0.6, rim);

  // Premultiplied output: the card is opaque, its shadow a soft dark veil.
  let shadowAlpha = 0.55 * shadow * (1.0 - silhouette);
  return vec4f(color * silhouette, silhouette + shadowAlpha);
}
