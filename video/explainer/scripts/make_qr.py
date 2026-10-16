"""QR code for the recruitment end card (src/EndCard.tsx). Needs `pip install qrcode`.
Usage: python3 scripts/make_qr.py [invite-url]  (default: web/assets/js/config.js's invite)"""
import re
import sys
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_Q

root = Path(__file__).resolve().parents[3]
config = (root / "web/assets/js/config.js").read_text()
url = sys.argv[1] if len(sys.argv) > 1 else re.search(r'DISCORD_INVITE_URL = "([^"]+)"', config).group(1)
qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, box_size=20, border=2)
qr.add_data(url)
qr.make(fit=True)
out = Path(__file__).resolve().parents[1] / "public/img/discord-qr.png"
qr.make_image(fill_color="#07120c", back_color="#ffffff").save(out)
print(f"{url} -> {out}")
