"""Build the static link-preview PNG. Requires Pillow; no runtime dependency."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def build(font_dir):
    scale = 2
    canvas = Image.new("RGB", (1200 * scale, 630 * scale), "#0b1420")
    draw = ImageDraw.Draw(canvas)

    def box(bounds, fill, radius=0, outline=None):
        draw.rounded_rectangle(tuple(int(n * scale) for n in bounds),
                               radius=radius * scale, fill=fill, outline=outline,
                               width=scale)

    def text(x, y, label, size, color, bold=False):
        font = ImageFont.truetype(str(font_dir / ("Arial Bold.ttf" if bold else "Arial.ttf")), size * scale)
        draw.text((x * scale, y * scale), label, font=font, fill=color)

    # Small brand mark; the message carries the preview.
    icon = Image.open(ROOT / "public/assets/tickr-digest-icon-t-concept.png").convert("RGBA")
    icon = icon.resize((48 * scale, 48 * scale), Image.Resampling.LANCZOS)
    canvas.paste(icon, (64 * scale, 54 * scale), icon)
    text(127, 62, "tickr digest", 30, "#f3f7fa", True)
    text(64, 157, "INDIAN STOCK RESEARCH", 19, "#aabaff", True)
    text(60, 201, "Understand", 72, "#f3f7fa", True)
    text(60, 280, "Indian stocks.", 72, "#f3f7fa", True)
    text(60, 359, "With AI.", 72, "#aabaff", True)
    text(64, 463, "A clearer starting point for your research.", 25, "#b9c7d7")

    box((752, 150, 1136, 487), "#121f2f", 26, "#2c3d51")
    text(782, 178, "FROM QUESTIONS TO CONTEXT", 15, "#aabaff", True)
    for y, number, title, detail in (
        (226, "01", "AI summaries", "Get to know the company"),
        (309, "02", "Company financials", "Explore the reported results"),
        (392, "03", "News & sources", "See the story behind the stock"),
    ):
        box((780, y, 828, y + 48), "#263657", 12)
        text(789, y + 13, number, 20, "#aabaff", True)
        text(844, y - 1, title, 23, "#f3f7fa", True)
        text(844, y + 31, detail, 17, "#b9c7d7")

    box((64, 535, 1136, 537), "#2c3d51")
    text(64, 558, "mydailydigest.online", 22, "#f3f7fa", True)
    text(796, 558, "Search without signing in", 22, "#a4eacb")
    output = ROOT / "public/assets/tickr-digest-share-v1.png"
    canvas.resize((1200, 630), Image.Resampling.LANCZOS).save(output, optimize=True)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir", type=Path, default=Path("/System/Library/Fonts/Supplemental"),
                        help="Directory containing Arial.ttf and Arial Bold.ttf")
    build(parser.parse_args().font_dir)
