"""Place editable SVG click markers over unchanged screenshot pixels.

Run from the repository root after updating docs/screenshot-annotations.json.
The original JPEG remains alongside each self-contained annotated SVG.
"""

import base64
import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main():
    entries = json.loads((ROOT / "docs/screenshot-annotations.json").read_text())
    for entry in entries:
        source = ROOT / entry["source"]
        width, height = entry["size"]
        canvas_width = width + entry.get("right_padding", 0)
        encoded = base64.b64encode(source.read_bytes()).decode("ascii")
        mime = "image/png" if source.suffix.lower() == ".png" else "image/jpeg"
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {canvas_width} {height}" width="{canvas_width}" height="{height}" '
            f'role="img" aria-labelledby="title description">',
            f'<title id="title">{escape(entry["title"])}</title>',
            '<desc id="description">Original Neurodesk VNC screenshot with '
            'numbered click targets. Screenshot pixels are unchanged.</desc>',
            f'<rect width="{canvas_width}" height="{height}" fill="white"/>',
            f'<image width="{width}" height="{height}" '
            f'xlink:href="data:{mime};base64,{encoded}"/>',
        ]
        for marker in entry["markers"]:
            x, y, w, h = marker["target"]
            cx, cy = marker["label"]
            tx, ty = marker["tip"]
            line = f'M {cx} {cy}' + ''.join(
                f' L {px} {py}' for px, py in marker.get('via', [])
            ) + f' L {tx} {ty}'
            parts.extend([
                f'<g><title>{escape(marker["text"])}</title>',
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                'rx="3" fill="none" stroke="white" stroke-width="5"/>',
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                'rx="3" fill="none" stroke="#e76f00" stroke-width="2.5"/>',
                f'<path d="{line}" fill="none" '
                'stroke="white" stroke-width="5"/>',
                f'<path d="{line}" fill="none" '
                'stroke="#e76f00" stroke-width="2.5"/>',
                f'<circle cx="{cx}" cy="{cy}" r="12" fill="#123c5a" '
                'stroke="white" stroke-width="2"/>',
                f'<text x="{cx}" y="{cy + 4.5}" text-anchor="middle" '
                'font-family="Arial, sans-serif" font-size="14" '
                f'font-weight="700" fill="white">{marker["number"]}</text></g>',
            ])
        parts.append('</svg>')
        destination = source.with_name(source.stem + '-annotated.svg')
        destination.write_text('\n'.join(parts) + '\n')
        print(destination.relative_to(ROOT))


if __name__ == '__main__':
    main()
