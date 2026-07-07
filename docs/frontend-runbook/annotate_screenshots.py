# ruff: noqa: E501
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "annotation-manifest.json"
OUT_DIR = ROOT / "annotated-screenshots"

PALETTE = [
    "#00A6B2",
    "#F59E0B",
    "#2563EB",
    "#DC2626",
    "#7C3AED",
    "#059669",
    "#E11D48",
    "#0F766E",
    "#B45309",
    "#4F46E5",
    "#9333EA",
    "#15803D",
    "#0369A1",
    "#BE123C",
]


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def clamp_rect(rect: dict[str, int], width: int, height: int) -> tuple[int, int, int, int]:
    x1 = max(0, min(width - 1, int(rect["x"])))
    y1 = max(0, min(height - 1, int(rect["y"])))
    x2 = max(0, min(width - 1, int(rect["x"] + rect["width"])))
    y2 = max(0, min(height - 1, int(rect["y"] + rect["height"])))
    if x2 <= x1:
        x2 = min(width - 1, x1 + 1)
    if y2 <= y1:
        y2 = min(height - 1, y1 + 1)
    return x1, y1, x2, y2


def draw_badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, color: str, font: ImageFont.ImageFont) -> None:
    text_box = draw.textbbox((0, 0), text, font=font)
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]
    pad_x = 9
    pad_y = 5
    box = (x, y, x + text_w + pad_x * 2, y + text_h + pad_y * 2)
    draw.rounded_rectangle(box, radius=8, fill=color, outline="white", width=2)
    draw.text((x + pad_x, y + pad_y - 1), text, fill="white", font=font)


def annotate_page(page: dict) -> None:
    image_path = Path(page["rawScreenshot"])
    out_path = Path(page["annotatedScreenshot"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path).convert("RGBA") as image:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = load_font(22)

        for box in page["screenshotInfo"]["boxes"]:
            if box.get("missing") or "rect" not in box:
                continue
            color = PALETTE[(box["id"] - 1) % len(PALETTE)]
            x1, y1, x2, y2 = clamp_rect(box["rect"], image.width, image.height)
            line_width = 5 if box["id"] <= 2 else 4
            draw.rectangle((x1, y1, x2, y2), outline=color, width=line_width)
            draw.rectangle((x1, y1, x2, y2), fill=color + "18")

            badge_x = min(max(x1 + 6, 4), image.width - 48)
            badge_y = min(max(y1 + 6, 4), image.height - 36)
            draw_badge(draw, badge_x, badge_y, str(box["id"]), color, font)

        annotated = Image.alpha_composite(image, overlay).convert("RGB")
        annotated.save(out_path, quality=94)


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for page in data["pages"]:
        annotate_page(page)


if __name__ == "__main__":
    main()
