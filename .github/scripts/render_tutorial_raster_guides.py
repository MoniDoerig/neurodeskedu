#!/usr/bin/env python3
"""Refresh tutorial-specific PNG click guides from native, unmarked captures."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    except OSError:
        font = ImageFont.load_default(size=18)
    for guide in json.loads((ROOT / "docs/tutorial-raster-guides.json").read_text()):
        image = Image.open(args.source_dir / guide["source"]).convert("RGB")
        if guide.get("right_padding"):
            padded = Image.new("RGB", (image.width + guide["right_padding"], image.height), "white")
            padded.paste(image, (0, 0))
            image = padded
        if image.size != tuple(guide["size"]):
            raise ValueError(f"Capture dimensions changed: {guide['source']}")
        draw = ImageDraw.Draw(image)
        for marker in guide["markers"]:
            x, y, w, h = marker["target"]
            box = (x, y, x + w, y + h)
            label, tip = tuple(marker["label"]), tuple(marker["tip"])
            draw.rounded_rectangle(box, radius=4, outline="white", width=6)
            draw.rounded_rectangle(box, radius=4, outline="#6aa329", width=3)
            draw.line([label, tip], fill="white", width=6)
            draw.line([label, tip], fill="#6aa329", width=3)
            cx, cy = label
            draw.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill="#456b1b", outline="white", width=2)
            value = str(marker["number"])
            left, top, right, bottom = draw.textbbox((0, 0), value, font=font)
            draw.text((cx - (left + right) / 2, cy - (top + bottom) / 2), value, font=font, fill="white")
        image.save(ROOT / guide["output"], format="PNG", optimize=True)


if __name__ == "__main__":
    main()
