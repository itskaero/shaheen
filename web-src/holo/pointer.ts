// The vGPU example's pointer maths (docs/DECISIONS.md ADR-117), unchanged
// except that upstream's framing constant 2.5 is a parameter. Pure, so it is
// unit-tested without a GPU.

export interface Rect {
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

export interface CardPointer {
  /** Pointer in card units: -1..1 across the card face, beyond it outside. */
  readonly pointerX: number;
  readonly pointerY: number;
  /** 0..1: how strongly the foil is revealed as the pointer approaches. */
  readonly targetHover: number;
}

export function cardPointer(rect: Rect, clientX: number, clientY: number, frame: number): CardPointer {
  const scale = Math.min(rect.height, rect.width * 1.35);
  // Match the shader's card coordinates and reveal the foil as the pointer approaches.
  const pointerX = ((clientX - rect.left) - rect.width / 2) / Math.max(1, scale) * frame / 0.64;
  const pointerY = ((clientY - rect.top) - rect.height / 2) / Math.max(1, scale) * frame / 0.91;
  const distanceX = Math.max(0, Math.abs(pointerX) - 1) * scale * 0.64 / frame;
  const distanceY = Math.max(0, Math.abs(pointerY) - 1) * scale * 0.91 / frame;
  // Begin revealing one full rendered card width beyond its edges.
  const approachDistance = Math.max(1, scale) * 1.28 / frame;
  const proximity = Math.max(0, 1 - Math.hypot(distanceX, distanceY) / approachDistance);
  return { pointerX, pointerY, targetHover: proximity * proximity * (3 - 2 * proximity) };
}
