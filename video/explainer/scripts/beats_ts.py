"""Writes src/beats.ts from the site's beat map for the soundtrack window used
by prepare_assets.py. Run from the repository root."""
import json
from pathlib import Path

from prepare_assets import MUSIC_END, MUSIC_START, ROOT

beats = json.loads((ROOT / "web/assets/audio/brawlistan.beats.json").read_text())
window = [
    [round(t - MUSIC_START, 3), s]
    for t, s in zip(beats["beats"], beats["strength"])
    if MUSIC_START - 0.01 <= t < MUSIC_END
]
out = Path(__file__).resolve().parents[1] / "src" / "beats.ts"
out.write_text(
    "// Beat times (seconds, video time) and strengths (0-9) for the soundtrack window,\n"
    "// from web/assets/audio/brawlistan.beats.json (scripts/beat_map.py), offset by the\n"
    f"// window start {MUSIC_START}s. Regenerate with scripts/beats_ts.py if the window changes.\n"
    f"export const BEATS: ReadonlyArray<readonly [number, number]> = {json.dumps(window)};\n"
)
print("wrote", out)
