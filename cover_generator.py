"""
Generates TikTok cover images by compositing an exact headline onto the
creator's uploaded photo.

Deliberately NOT using an AI image model to render the text or restyle the
photo. Diffusion models are unreliable at exact spelling and commonly alter
a person's face when re-generating an image -- both of which the cover spec
explicitly forbids ("never misspell", "preserve recognizable appearance").
Pillow guarantees both: the photo pixels are never regenerated, and the
headline is drawn as literal text, so what you type is exactly what renders.
"""

import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps

CANVAS_W, CANVAS_H = 1080, 1920

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_BOLD_SANS = os.path.join(FONT_DIR, "Outfit-Bold.ttf")
FONT_LUXURY_SERIF = os.path.join(FONT_DIR, "Gloock-Regular.ttf")

# Safe zone: center portion of the canvas, away from top/bottom/edges,
# so the headline survives TikTok's UI crop.
SAFE_TOP = int(CANVAS_H * 0.36)
SAFE_BOTTOM = int(CANVAS_H * 0.64)
SAFE_LEFT = int(CANVAS_W * 0.09)
SAFE_RIGHT = int(CANVAS_W * 0.91)
SAFE_WIDTH = SAFE_RIGHT - SAFE_LEFT
SAFE_HEIGHT = SAFE_BOTTOM - SAFE_TOP

# style -> (font path, saturation, contrast, brightness, scrim darkness 0-255)
STYLE_CONFIG = {
    "bold": (FONT_BOLD_SANS, 1.25, 1.20, 1.02, 190),
    "clean": (FONT_BOLD_SANS, 1.00, 1.05, 1.03, 140),
    "luxury": (FONT_LUXURY_SERIF, 0.85, 1.10, 0.95, 170),
    "fun": (FONT_BOLD_SANS, 1.40, 1.15, 1.08, 150),
    "food": (FONT_BOLD_SANS, 1.30, 1.10, 1.05, 160),
    "travel": (FONT_BOLD_SANS, 1.20, 1.12, 1.04, 150),
    "dramatic": (FONT_BOLD_SANS, 1.05, 1.35, 0.90, 210),
}


def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize+center-crop to exactly fill target dimensions (like CSS object-fit: cover)."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _draw_scrim(base: Image.Image, darkness: int) -> Image.Image:
    """Soft dark gradient band behind the safe zone, so text stays readable on any photo."""
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    fade = int(SAFE_HEIGHT * 0.35)
    band_top = max(0, SAFE_TOP - fade)
    band_bottom = min(CANVAS_H, SAFE_BOTTOM + fade)

    for y in range(band_top, band_bottom):
        if y < SAFE_TOP:
            t = (y - band_top) / max(1, (SAFE_TOP - band_top))
        elif y > SAFE_BOTTOM:
            t = 1 - (y - SAFE_BOTTOM) / max(1, (band_bottom - SAFE_BOTTOM))
        else:
            t = 1.0
        alpha = int(darkness * t)
        draw.line([(0, y), (CANVAS_W, y)], fill=(0, 0, 0, alpha))

    return Image.alpha_composite(base.convert("RGBA"), overlay)


def _fit_text(draw: ImageDraw.ImageDraw, headline: str, font_path: str) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Find the largest font size where the wrapped headline fits the safe zone."""
    words = headline.split()
    max_size, min_size = 130, 42

    for size in range(max_size, min_size - 1, -4):
        font = ImageFont.truetype(font_path, size)
        lines, current = [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if draw.textlength(candidate, font=font) <= SAFE_WIDTH:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        line_height = int(size * 1.25)
        total_height = line_height * len(lines)
        widest = max((draw.textlength(line, font=font) for line in lines), default=0)

        if total_height <= SAFE_HEIGHT and widest <= SAFE_WIDTH and len(lines) <= 5:
            return font, lines

    # Fallback: smallest size, hard-accept whatever wrapping results
    font = ImageFont.truetype(font_path, min_size)
    return font, [headline]


def generate_cover(image_bytes: bytes, headline: str, style: str) -> bytes:
    """
    Main entry point. Takes the raw uploaded photo bytes, exact headline text,
    and a style key (see STYLE_CONFIG), and returns PNG bytes for the finished
    1080x1920 cover.
    """
    style = style if style in STYLE_CONFIG else "clean"
    font_path, saturation, contrast, brightness, darkness = STYLE_CONFIG[style]

    img = Image.open(BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)  # respect phone camera rotation metadata
    img = img.convert("RGB")

    img = _cover_crop(img, CANVAS_W, CANVAS_H)

    img = ImageEnhance.Color(img).enhance(saturation)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Brightness(img).enhance(brightness)

    composed = _draw_scrim(img, darkness)

    draw = ImageDraw.Draw(composed)
    font, lines = _fit_text(draw, headline, font_path)

    line_height = int(font.size * 1.25)
    total_height = line_height * len(lines)
    start_y = SAFE_TOP + (SAFE_HEIGHT - total_height) // 2

    stroke_width = max(2, font.size // 22)
    for i, line in enumerate(lines):
        width = draw.textlength(line, font=font)
        x = SAFE_LEFT + (SAFE_WIDTH - width) / 2
        y = start_y + i * line_height
        draw.text(
            (x, y), line, font=font,
            fill=(255, 255, 255, 255),
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0, 255),
        )

    out = BytesIO()
    composed.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
