#!/usr/bin/env python3
import sys
import os

try:
    import qrcode
except ImportError:
    print("Missing dependency: qrcode. Install with: pip install qrcode[pil]")
    sys.exit(1)

from qrcode.constants import ERROR_CORRECT_M

def make_qr(url: str, out_path: str, size_px: int = 512) -> None:
    # Create QR with decent error correction
    qr = qrcode.QRCode(
        version=None,  # auto-fit
        error_correction=ERROR_CORRECT_M,
        box_size=10,   # will be resized later anyway
        border=4
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    # Force exact size 512x512 using nearest-neighbor to keep edges crisp
    img = img.resize((size_px, size_px), resample=0)
    img.save(out_path, format="PNG")

def main():
    if len(sys.argv) < 2:
        print("Usage: python make_qr.py <URL> [output.png]")
        sys.exit(1)

    url = sys.argv[1].strip()
    out_path = sys.argv[2].strip() if len(sys.argv) >= 3 else "qrcode.png"

    if not (url.startswith("http://") or url.startswith("https://")):
        print("Warning: URL does not start with http:// or https://, encoding anyway.")

    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    make_qr(url, out_path, 512)
    print(f"Saved QR code to {out_path} (512x512)")

if __name__ == "__main__":
    main()
