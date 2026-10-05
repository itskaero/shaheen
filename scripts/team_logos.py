"""Cut team logos for the website and Discord (docs/DECISIONS.md ADR-114).

    python scripts/team_logos.py

Every docs/brand/teams/<slug>-master.png becomes
web/assets/img/teams/<slug>.{webp,png}: a 512px square, transparent around
the art so it sits on any surface. A master on black (like most esports
logos) is keyed with the same colour-to-alpha as the BRAWLISTAN logo, so its
glow survives; a master that already has transparency is used as is.

To add a team's logo: save it as docs/brand/teams/<team-slug>-master.png,
run this, and make sure the team's `logo` is <team-slug>.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageMath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brand_assets import colour_to_alpha, save_pair, trim  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MASTERS = ROOT / "docs" / "brand" / "teams"
OUT = ROOT / "web" / "assets" / "img" / "teams"
SIZE = 512
PAD = 0.06  # breathing room around the art, as a share of the square


def has_transparency(img: Image.Image) -> bool:
    if img.mode == "P":
        return "transparency" in img.info
    return img.mode in ("RGBA", "LA") and img.getchannel("A").getextrema()[0] < 250


def square(img: Image.Image) -> Image.Image:
    side = round(max(img.size) * (1 + 2 * PAD))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


def key_on_black(img: Image.Image) -> Image.Image:
    """Colour-to-alpha, but dark-and-not-black art stays solid.

    Pure colour-to-alpha (brand_assets.colour_to_alpha) makes every dark
    colour translucent, which suits neon logos and washes out darker ones
    (a grey wolf, black stone, deep red lettering). Here alpha is the larger
    of that and a soft "is this not background" mask, and the colour is
    un-premultiplied against that alpha, so glows still fade out smoothly
    while the body of the art stays opaque (ADR-120).
    """
    rgb = img.convert("RGB")
    glow = colour_to_alpha(rgb).getchannel("A")
    brightest = ImageChops.lighter(ImageChops.lighter(*rgb.split()[:2]), rgb.split()[2])
    body = brightest.point(lambda v: min(255, max(0, round((v - 18) * 255 / 36))))
    alpha = ImageChops.lighter(glow, body)
    channels = [
        ImageMath.lambda_eval(
            lambda ns: ns["min"](ns["c"] * 255 / ns["max"](ns["a"], 1), 255),
            c=channel.convert("F"),
            a=alpha.convert("F"),
        ).convert("L")
        for channel in rgb.split()
    ]
    return Image.merge("RGBA", (*channels, alpha))


def cut(master: Path) -> Path:
    src = Image.open(master)
    art = src.convert("RGBA") if has_transparency(src) else key_on_black(src)
    stem = OUT / master.name.removesuffix("-master.png")
    save_pair(square(trim(art)), stem)
    return stem


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for master in sorted(MASTERS.glob("*-master.png")):
        print(f"{master.name} -> {cut(master).relative_to(ROOT)}.{{webp,png}}")


if __name__ == "__main__":
    main()
