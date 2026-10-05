// Team colours from markup (docs/DECISIONS.md ADR-117). Pure, unit-tested.

export type Rgb = readonly [number, number, number];

/** "#3df26e" -> [0.24, 0.95, 0.43]; anything else -> fallback. */
export function parseColor(value: string | undefined, fallback: Rgb): Rgb {
  const hex = (value ?? '').trim().replace(/^#/, '');
  if (!/^[0-9a-f]{6}$/i.test(hex)) return fallback;
  return [
    parseInt(hex.slice(0, 2), 16) / 255,
    parseInt(hex.slice(2, 4), 16) / 255,
    parseInt(hex.slice(4, 6), 16) / 255,
  ];
}
