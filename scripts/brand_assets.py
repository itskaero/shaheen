"""Cut the BRAWLISTAN web/app assets from the owner's master logo.

    python scripts/brand_assets.py

Re-runnable: replace docs/brand/brawlistan-logo-master.png with new art and
run again (docs/DECISIONS.md ADR-104). The master is 1254x1254 on near-black;
"colour to alpha" against black keeps the neon glow on any dark surface, so
the site never needs a black box around the logo.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageMath

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "docs" / "brand" / "brawlistan-logo-master.png"
BANNER_MASTER = ROOT / "docs" / "brand" / "brawlistan-banner-master.png"
SEASONS_MASTER = ROOT / "docs" / "brand" / "brawlistan-seasons-master.png"

WEB = ROOT / "web" / "assets" / "img"
OUT = WEB / "brawlistan"
WEB_SEASONS = WEB / "seasons"
BOT_SEASONS = ROOT / "src" / "assets" / "img" / "seasons"

# Regions of the master, in master pixels (left, top, right, bottom).
WORDMARK_BOX = (40, 605, 1230, 1005)  # BRAWLISTAN + "Pakistan's Brawlhalla Network"
MARK_BOX = (560, 170, 1010, 620)  # crescent, star and the falcon's eye
BLACK = (5, 5, 6)

# The season sheet's 13 cards in season order (ADR-108): 5 + 5 + 3 on black
# gutters, found from the sheet's row/column projections. Each region is
# padded a little and then trimmed to the card's own edges.
SEASON_CARD_BOXES = (
    (6, 19, 341, 331),
    (360, 19, 665, 331),
    (685, 19, 990, 331),
    (1009, 19, 1313, 331),
    (1331, 19, 1665, 331),
    (10, 366, 341, 647),
    (361, 366, 674, 647),
    (693, 366, 981, 647),
    (1000, 366, 1312, 647),
    (1331, 366, 1660, 647),
    (62, 670, 555, 919),
    (595, 670, 1094, 919),
    (1128, 670, 1606, 919),
)


def colour_to_alpha(img: Image.Image) -> Image.Image:
    """Black becomes transparent; everything else keeps its exact look on black.

    alpha = the brightest channel (minus a small near-black noise floor), and
    each channel is divided by alpha so the colour composited back over black
    is the original pixel.
    """
    r, g, b = img.convert("RGB").split()
    brightest = ImageChops.lighter(ImageChops.lighter(r, g), b)
    alpha = brightest.point(lambda v: max(0, min(255, round((v - 8) * 255 / 247))))

    def unmultiply(channel: Image.Image) -> Image.Image:
        out = ImageMath.lambda_eval(
            lambda ns: ns["min"](ns["c"] * 255 / ns["max"](ns["a"], 1), 255),
            c=channel.convert("F"),
            a=brightest.convert("F"),
        )
        return out.convert("L")

    return Image.merge("RGBA", (unmultiply(r), unmultiply(g), unmultiply(b), alpha))


def _ramp(length: int, start: int, end: int) -> Image.Image:
    """A 1-pixel-wide 0→255→0 ramp: fades in over `start`, out over `end`."""
    ramp = Image.new("L", (1, length), 255)
    for i in range(start):
        ramp.putpixel((0, i), round(255 * i / start))
    for i in range(end):
        ramp.putpixel((0, length - 1 - i), round(255 * i / end))
    return ramp


def fade_edges(
    img: Image.Image, *, top: int = 0, bottom: int = 0, left: int = 0, right: int = 0
) -> Image.Image:
    """Feather the edges so a crop doesn't end in a hard line."""
    w, h = img.size
    vertical = _ramp(h, top, bottom).resize((w, h))
    horizontal = _ramp(w, left, right).transpose(Image.Transpose.ROTATE_270).resize((w, h))
    r, g, b, a = img.split()
    mask = ImageChops.multiply(vertical, horizontal)
    return Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, mask)))


def fade_round(img: Image.Image) -> Image.Image:
    """Soft circular edge, for the mark used inside pages."""
    w, h = img.size
    radius = min(w, h) / 2
    mask = Image.new("L", (w, h))
    values = []
    for y in range(h):
        for x in range(w):
            d = ((x + 0.5 - w / 2) ** 2 + (y + 0.5 - h / 2) ** 2) ** 0.5 / radius  # 0..1 at edge
            values.append(255 if d < 0.72 else max(0, round(255 * (1 - d) / 0.28)))
    mask.putdata(values)
    r, g, b, a = img.split()
    return Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, mask)))


def trim(img: Image.Image) -> Image.Image:
    box = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    return img.crop(box) if box else img


def save_pair(img: Image.Image, stem: Path, *, quality: int = 80) -> None:
    """WebP for browsers that take it, a 256-colour PNG fallback for the rest."""
    img.save(stem.with_suffix(".webp"), quality=quality, method=6)
    fallback = img.quantize(256, method=Image.Quantize.FASTOCTREE)
    fallback.save(stem.with_suffix(".png"), optimize=True)


def by_height(img: Image.Image, height: int) -> Image.Image:
    return img.resize((round(img.width * height / img.height), height), Image.LANCZOS)


def by_width(img: Image.Image, width: int) -> Image.Image:
    return img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    master = Image.open(MASTER).convert("RGB")

    logo = trim(colour_to_alpha(master))
    save_pair(by_width(logo, 720), OUT / "logo")

    wordmark = fade_edges(
        colour_to_alpha(master.crop(WORDMARK_BOX)), top=40, bottom=24, left=30, right=30
    )
    save_pair(by_height(trim(wordmark), 132), OUT / "wordmark")

    mark_square = master.crop(MARK_BOX)
    save_pair(by_width(fade_round(colour_to_alpha(mark_square)), 256), OUT / "mark")
    # App/browser icons: opaque, on the logo's own black.
    for size, path in (
        (32, WEB / "favicon-32.png"),
        (48, WEB / "favicon-48.png"),
        (180, WEB / "apple-touch-icon.png"),
        (192, OUT / "icon-192.png"),
        (512, OUT / "icon-512.png"),
    ):
        icon = mark_square.resize((size, size), Image.LANCZOS)
        icon.quantize(256, method=Image.Quantize.FASTOCTREE).save(path, optimize=True)

    banner = Image.open(BANNER_MASTER).convert("RGB")
    wide = by_width(banner, 1600)
    wide.save(OUT / "banner.webp", quality=82, method=6)
    wide.save(OUT / "banner.jpg", quality=84, optimize=True, progressive=True)

    # Open Graph / Twitter card: 1200x630 from the banner's centre, which is
    # where the logo sits.
    og = by_height(banner, 630)
    left = (og.width - 1200) // 2
    og.crop((left, 0, left + 1200, 630)).save(OUT / "og-card.jpg", quality=86, optimize=True)

    cut_season_cards()


def _trim_dark(img: Image.Image) -> Image.Image:
    """Crop to the card itself, dropping the sheet's black gutter."""
    mask = img.convert("L").point(lambda v: 255 if v > 26 else 0)
    box = mask.getbbox()
    return img.crop(box) if box else img


def cut_season_cards() -> None:
    sheet = Image.open(SEASONS_MASTER).convert("RGB")
    WEB_SEASONS.mkdir(parents=True, exist_ok=True)
    BOT_SEASONS.mkdir(parents=True, exist_ok=True)
    pad = 10
    for number, (x0, y0, x1, y1) in enumerate(SEASON_CARD_BOXES, start=1):
        region = (
            max(0, x0 - pad),
            max(0, y0 - pad),
            min(sheet.width, x1 + pad),
            min(sheet.height, y1 + pad),
        )
        card = _trim_dark(sheet.crop(region))
        stem = f"{number:02d}"
        web_card = by_height(card, 320) if card.height > 320 else card
        web_card.save(WEB_SEASONS / f"{stem}.webp", quality=84, method=6)
        web_card.save(WEB_SEASONS / f"{stem}.jpg", quality=86, optimize=True, progressive=True)
        card.save(BOT_SEASONS / f"{stem}.jpg", quality=90, optimize=True)


if __name__ == "__main__":
    main()
