"""
Generates TikTok cover images by compositing an exact headline onto the
creator's uploaded photo.

Deliberately NOT using an AI image model to render the text or restyle the
photo. Diffusion models are unreliable at exact spelling and commonly alter
a person's face when re-generating an image -- both of which the cover spec
explicitly forbids ("never misspell", "preserve recognizable appearance").
Pillow guarantees both: the photo pixels are never regenerated, and the
headline is drawn as literal text, so what you type is exactly what renders.

Typography styled after poster-style covers: a bold main line + a colored
script accent word, drop shadows instead of a flat dark bar, slight tilt
on the accent for energy.
"""

import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImageFilter

CANVAS_W, CANVAS_H = 1080, 1920

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_MAIN_SANS = os.path.join(FONT_DIR, "BigShoulders-Bold.ttf")      # punchy condensed bold
FONT_MAIN_CLEAN = os.path.join(FONT_DIR, "Outfit-Bold.ttf")            # calmer bold sans
FONT_LUXURY_SERIF = os.path.join(FONT_DIR, "Gloock-Regular.ttf")       # elegant editorial serif
FONT_ACCENT_SCRIPT = os.path.join(FONT_DIR, "NothingYouCouldDo-Regular.ttf")  # brush script accent

for _path in (FONT_MAIN_SANS, FONT_MAIN_CLEAN, FONT_LUXURY_SERIF, FONT_ACCENT_SCRIPT):
    if not os.path.isfile(_path):
        raise FileNotFoundError(
            f"Missing font file: {_path}\n"
            "The 'fonts' folder didn't make it into this deployment. "
            "Make sure every .ttf in fonts/ is committed to git and pushed."
        )

# Safe zone: center portion of the canvas, away from top/bottom/edges,
# so the headline survives TikTok's UI crop.
SAFE_TOP = int(CANVAS_H * 0.32)
SAFE_BOTTOM = int(CANVAS_H * 0.68)
SAFE_LEFT = int(CANVAS_W * 0.08)
SAFE_RIGHT = int(CANVAS_W * 0.92)
SAFE_WIDTH = SAFE_RIGHT - SAFE_LEFT
SAFE_HEIGHT = SAFE_BOTTOM - SAFE_TOP

# style -> (main_font, accent_font, main_color, accent_color, saturation, contrast, brightness)
STYLE_CONFIG = {
    "bold":     (FONT_MAIN_SANS,   FONT_ACCENT_SCRIPT, (255, 255, 255), (255, 209, 0), 1.25, 1.20, 1.02),
    "clean":    (FONT_MAIN_CLEAN,  FONT_MAIN_CLEAN,    (255, 255, 255), (255, 255, 255), 1.00, 1.05, 1.03),
    "luxury":   (FONT_LUXURY_SERIF, FONT_LUXURY_SERIF, (250, 245, 235), (212, 175, 90), 0.85, 1.10, 0.95),
    "fun":      (FONT_MAIN_SANS,   FONT_ACCENT_SCRIPT, (255, 255, 255), (255, 90, 160), 1.40, 1.15, 1.08),
    "food":     (FONT_MAIN_SANS,   FONT_ACCENT_SCRIPT, (255, 255, 255), (255, 140, 40), 1.30, 1.10, 1.05),
    "travel":   (FONT_MAIN_SANS,   FONT_ACCENT_SCRIPT, (255, 255, 255), (80, 210, 210), 1.20, 1.12, 1.04),
    "dramatic": (FONT_MAIN_SANS,   FONT_ACCENT_SCRIPT, (255, 255, 255), (230, 50, 50), 1.05, 1.35, 0.90),
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


def _wrap_to_width(draw: ImageDraw.ImageDraw, words: list[str], font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_main_lines(draw: ImageDraw.ImageDraw, words: list[str], font_path: str, max_height: int):
    """Shrink font size until wrapped main-line text fits the safe width and given height budget."""
    if not words:
        return None, []
    for size in range(110, 36, -4):
        font = ImageFont.truetype(font_path, size)
        lines = _wrap_to_width(draw, words, font, SAFE_WIDTH)
        line_height = int(size * 1.15)
        if line_height * len(lines) <= max_height and len(lines) <= 3:
            return font, lines
    font = ImageFont.truetype(font_path, 36)
    return font, _wrap_to_width(draw, words, font, SAFE_WIDTH)


def _fit_accent_word(draw: ImageDraw.ImageDraw, word: str, font_path: str, max_width: int):
    """Shrink font size until the single accent word fits the safe width."""
    for size in range(180, 40, -4):
        font = ImageFont.truetype(font_path, size)
        if draw.textlength(word, font=font) <= max_width:
            return font
    return ImageFont.truetype(font_path, 40)


def _draw_text_with_shadow(base: Image.Image, text: str, font: ImageFont.FreeTypeFont,
                            xy: tuple, fill: tuple, shadow_opacity: int = 165,
                            shadow_offset: tuple = (0, 6), shadow_blur: int = 10,
                            stroke_width: int = 0) -> None:
    """Draws soft drop-shadow text directly onto base (RGBA)."""
    x, y = xy

    shadow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.text(
        (x + shadow_offset[0], y + shadow_offset[1]), text, font=font,
        fill=(0, 0, 0, shadow_opacity),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))
    base.alpha_composite(shadow_layer)

    draw = ImageDraw.Draw(base)
    draw.text(
        (x, y), text, font=font, fill=(*fill, 255),
        stroke_width=stroke_width, stroke_fill=(0, 0, 0, 200),
    )


def _render_rotated_text(text: str, font: ImageFont.FreeTypeFont, color: tuple, angle: float,
                          shadow_opacity: int = 170) -> Image.Image:
    """Renders a single line of text (with shadow) onto its own transparent canvas, then rotates it."""
    bbox = ImageDraw.Draw(Image.new("RGBA", (10, 10))).textbbox((0, 0), text, font=font)
    pad = 40
    w = (bbox[2] - bbox[0]) + pad * 2
    h = (bbox[3] - bbox[1]) + pad * 2

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    _draw_text_with_shadow(
        layer, text, font, (pad - bbox[0], pad - bbox[1]), color,
        shadow_opacity=shadow_opacity, shadow_offset=(3, 8), shadow_blur=8,
    )
    return layer.rotate(angle, expand=True, resample=Image.BICUBIC)


def generate_cover(image_bytes: bytes, headline: str, style: str) -> bytes:
    """
    Main entry point. Takes the raw uploaded photo bytes, exact headline text,
    and a style key (see STYLE_CONFIG), and returns PNG bytes for the finished
    1080x1920 cover.
    """
    style = style if style in STYLE_CONFIG else "clean"
    main_font_path, accent_font_path, main_color, accent_color, saturation, contrast, brightness = STYLE_CONFIG[style]

    img = Image.open(BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)  # respect phone camera rotation metadata
    img = img.convert("RGB")
    img = _cover_crop(img, CANVAS_W, CANVAS_H)

    img = ImageEnhance.Color(img).enhance(saturation)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Brightness(img).enhance(brightness)

    canvas = img.convert("RGBA")
    measure_draw = ImageDraw.Draw(canvas)

    # Split headline: everything but the last word is the "main" line(s) in
    # the primary font/color; the last word becomes a larger script accent,
    # mirroring the two-tone stacked look (e.g. "Reunion" / "Hotel").
    words = headline.split()
    use_accent = len(words) >= 2 and style != "clean"
    main_words = words[:-1] if use_accent else words
    accent_word = words[-1] if use_accent else None

    accent_font = None
    accent_img = None
    if accent_word:
        accent_font = _fit_accent_word(measure_draw, accent_word, accent_font_path, SAFE_WIDTH)
        tilt = -5 if style in ("bold", "fun", "dramatic") else 0
        accent_img = _render_rotated_text(accent_word, accent_font, accent_color, tilt)

    accent_height = accent_img.height if accent_img else 0
    main_font, main_lines = _fit_main_lines(
        measure_draw, main_words, main_font_path, max_height=SAFE_HEIGHT - accent_height - 20
    )

    main_line_height = int(main_font.size * 1.15) if main_font else 0
    main_block_height = main_line_height * len(main_lines)
    total_height = main_block_height + (accent_height + 10 if accent_img else 0)
    start_y = SAFE_TOP + max(0, (SAFE_HEIGHT - total_height) // 2)

    y = start_y
    stroke_width = max(2, main_font.size // 24) if main_font else 0
    for line in main_lines:
        width = measure_draw.textlength(line, font=main_font)
        x = SAFE_LEFT + (SAFE_WIDTH - width) / 2
        _draw_text_with_shadow(canvas, line, main_font, (x, y), main_color, stroke_width=stroke_width)
        y += main_line_height

    if accent_img:
        ax = SAFE_LEFT + (SAFE_WIDTH - accent_img.width) / 2
        canvas.alpha_composite(accent_img, (int(ax), int(y - 6)))

    out = BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
