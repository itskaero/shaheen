"""Fetch the achievement-card badge icons (docs/DECISIONS.md ADR-124).

Each achievement gets one Noto Emoji image (Google, CC BY 4.0 / Apache-2.0),
downloaded at 512 px from Google's font CDN and saved at 256 px as
src/assets/achievement_icons/<key>.png. `_default.png` covers any achievement
added later without an icon. Run again after changing ICONS:

    python scripts/achievement_icons.py
"""

from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "assets" / "achievement_icons"
SIZE = 256
URL = "https://fonts.gstatic.com/s/e/notoemoji/latest/{code}/512.png"

# Achievement key -> emoji codepoint (as Noto names it).
ICONS: dict[str, str] = {
    "_default": "1f3c5",  # 🏅
    "first_link": "1f517",  # 🔗
    "games_100": "2694_fe0f",  # ⚔️
    "games_500": "1f6e1_fe0f",  # 🛡️
    "games_1000": "1f396_fe0f",  # 🎖️
    "games_2500": "1f525",  # 🔥
    "games_5000": "1f4aa",  # 💪
    "tier_gold": "1f947",  # 🥇
    "tier_platinum": "1f4a0",  # 💠
    "tier_diamond_plus": "1f48e",  # 💎
    "tier_valhallan": "1f451",  # 👑
    "peak_1500": "1f4c8",  # 📈
    "peak_1800": "1f985",  # 🦅
    "peak_2000": "1f320",  # 🌠
    "global_top_1000": "1f30d",  # 🌍
    "region_top_100": "1f5fa_fe0f",  # 🗺️
    "win_rate_60": "1f3af",  # 🎯
    "first_win": "1f5e1_fe0f",  # 🗡️
    "wins_10": "1f94a",  # 🥊
    "wins_50": "26a1",  # ⚡
    "tournament_entrant": "1f39f_fe0f",  # 🎟️
    "tournament_finalist": "1f948",  # 🥈
    "tournament_champion": "1f3c6",  # 🏆
    "scrim_regular": "1f91d",  # 🤝
    "chat_level_10": "1f4ac",  # 💬
    "chat_level_25": "1f4e3",  # 📣
    "chat_level_50": "1fab6",  # 🪶
    "mvp_of_week": "1f31f",  # 🌟
    "veteran_30d": "1f319",  # 🌙
    "veteran_180d": "26f0_fe0f",  # ⛰️
    "veteran_365d": "1f386",  # 🎆
}


def fetch(code: str) -> Image.Image:
    candidates = [code, code.removesuffix("_fe0f")]
    for candidate in dict.fromkeys(candidates):
        request = urllib.request.Request(
            URL.format(code=candidate), headers={"User-Agent": "brawlistan-icons"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return Image.open(io.BytesIO(response.read())).convert("RGBA")
        except OSError:
            continue
    raise SystemExit(f"No Noto image for {code}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for key, code in ICONS.items():
        icon = fetch(code)
        bbox = icon.getchannel("A").getbbox()
        if bbox:
            icon = icon.crop(bbox)
        # Square, centred, then 256 px.
        side = max(icon.size)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2))
        square.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(
            OUT / f"{key}.png", optimize=True
        )
        print(key, code)
    return 0


if __name__ == "__main__":
    sys.exit(main())
