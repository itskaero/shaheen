import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cardPointer } from './pointer.ts';
import { parseColor } from './color.ts';

// A canvas with the card's own aspect (20:27), so scale = height.
const rect = { left: 0, top: 0, width: 400, height: 540 };
const FRAME = 2.1;

test('the centre of the card is pointer (0, 0) and fully revealed', () => {
  const p = cardPointer(rect, 200, 270, FRAME);
  assert.equal(p.pointerX, 0);
  assert.equal(p.pointerY, 0);
  assert.equal(p.targetHover, 1);
});

test('the card edge is pointer +/-1 and still fully revealed', () => {
  // Card half-width in px = 0.64 card units * (540 / 2.1).
  const edge = 200 + 0.64 * (540 / FRAME);
  const p = cardPointer(rect, edge, 270, FRAME);
  assert.ok(Math.abs(p.pointerX - 1) < 1e-9);
  assert.equal(p.targetHover, 1);
});

test('the reveal fades out one card width beyond the edge', () => {
  const cardWidth = 1.28 * (540 / FRAME);
  const edge = 200 + 0.64 * (540 / FRAME);
  const half = cardPointer(rect, edge + cardWidth / 2, 270, FRAME).targetHover;
  const far = cardPointer(rect, edge + cardWidth * 1.01, 270, FRAME).targetHover;
  assert.ok(half > 0 && half < 1);
  assert.equal(far, 0);
});

test('team colours parse from hex and fall back otherwise', () => {
  const fallback = [0, 0, 0] as const;
  assert.deepEqual(parseColor('#ff0080', fallback), [1, 0, 128 / 255]);
  assert.deepEqual(parseColor('00FF00', fallback), [0, 1, 0]);
  assert.equal(parseColor('red', fallback), fallback);
  assert.equal(parseColor(undefined, fallback), fallback);
});
