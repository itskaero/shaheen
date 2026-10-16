"""Tiles rendered stills into one image for review: contact_sheet.py out.jpg a.jpg b.jpg ..."""
import sys

from PIL import Image, ImageDraw

out, *files = sys.argv[1:]
cols = 3
w, h = 640, 360
sheet = Image.new("RGB", (cols * w, ((len(files) + cols - 1) // cols) * h), "black")
for i, path in enumerate(files):
    im = Image.open(path).convert("RGB").resize((w, h))
    ImageDraw.Draw(im).text((8, 6), path.rsplit("/", 1)[-1], fill="yellow")
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(out, quality=85)
