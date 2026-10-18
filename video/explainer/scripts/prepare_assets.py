"""Copies and prepares the site's own art and music for the explainer.

Run from the repository root: python3 video/explainer/scripts/prepare_assets.py
Everything comes from web/ or docs/brand/ (the owner's art and original tracks).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from brand_assets import colour_to_alpha, trim  # noqa: E402  (the site's own keying)

WEB = ROOT / "web" / "assets"
PUB = ROOT / "video" / "explainer" / "public"

# The soundtrack window inside "Brawlistan" (web/assets/audio/brawlistan.mp3):
# starts on a beat just before the hit at 130.5 s, the drop at 157.06 s lands on
# City Wars, and it ends where the track dips at 193.5 s.
MUSIC_START = 129.335
MUSIC_END = 193.5


def main() -> None:
    (PUB / "img" / "teams").mkdir(parents=True, exist_ok=True)
    (PUB / "audio").mkdir(parents=True, exist_ok=True)

    master = Image.open(ROOT / "docs" / "brand" / "brawlistan-logo-master.png").convert("RGB")
    trim(colour_to_alpha(master)).save(PUB / "img" / "logo.png")

    for name in ("warriors.jpg", "hero-scene.jpg", "banner.jpg", "mark.png"):
        shutil.copy(WEB / "img" / "brawlistan" / name, PUB / "img" / name)
    for team in ("sigma-grinders", "delight-esports", "clan-monke", "revenant-wolf", "shaheen"):
        shutil.copy(WEB / "img" / "teams" / f"{team}.png", PUB / "img" / "teams" / f"{team}.png")

    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-ss", str(MUSIC_START), "-to", str(MUSIC_END),
            "-i", str(WEB / "audio" / "brawlistan.mp3"),
            "-af", f"afade=t=out:st={MUSIC_END - MUSIC_START - 0.6}:d=0.6",
            "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "256k", str(PUB / "audio" / "music.mp3"),
        ],
        check=True,
    )
    print("assets ready in", PUB)


if __name__ == "__main__":
    main()
