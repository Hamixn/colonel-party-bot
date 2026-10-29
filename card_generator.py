import io
import math
import random
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

import config

def reshape_persian(text: str) -> str:
    """Properly reshapes and reverses Persian/Arabic text for Pillow RTL rendering."""
    if not text:
        return ""
    configuration = {
        'delete_harakat': False,
        'support_ligatures': True,
    }
    reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
    reshaped_text = reshaper.reshape(text)
    return get_display(reshaped_text)

def get_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
    """
    Safely loads TrueType font with fallback.
    Explicitly forces BASIC layout engine to ensure identical, correct RTL rendering
    on Linux (where Pillow defaults to Raqm, causing double-bidi reversal/letter disconnection).
    """
    if font_path.exists():
        try:
            if hasattr(ImageFont, 'Layout') and hasattr(ImageFont.Layout, 'BASIC'):
                return ImageFont.truetype(str(font_path), size, layout_engine=ImageFont.Layout.BASIC)
            return ImageFont.truetype(str(font_path), size)
        except Exception:
            try:
                return ImageFont.truetype(str(font_path), size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int],
    canvas_width: int,
    is_persian: bool = True
) -> int:
    """Draws horizontally centered text. Returns bottom Y coordinate."""
    display_text = reshape_persian(text) if is_persian else text
    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (canvas_width - text_width) // 2
    draw.text((x, y), display_text, font=font, fill=fill)
    return y + text_height

def prepare_background(width: int, height: int) -> Image.Image:
    """
    Loads user's custom gothic mansion background and prepares it
    with a subtle dark gradient/vignette on the lower text area.
    """
    if config.CARD_BG_PATH.exists():
        try:
            bg = Image.open(config.CARD_BG_PATH).convert("RGBA")
            bg = bg.resize((width, height), Image.Resampling.LANCZOS)

            # Darkening overlay specifically for the text area (Y=380 to Y=1250)
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw_ov = ImageDraw.Draw(overlay)

            # Smooth vertical gradient overlay to make text pop while keeping gate/moon visible
            for current_y in range(350, height - 70):
                alpha = int(185 * min(1.0, (current_y - 350) / 100))
                draw_ov.line([(70, current_y), (width - 70, current_y)], fill=(8, 5, 8, alpha))

            return Image.alpha_composite(bg, overlay).convert("RGB")
        except Exception as e:
            print(f"Error loading background image: {e}")

    # Fallback procedural
    base = np.full((height, width, 3), [14, 11, 14], dtype=np.int16)
    noise = np.random.randint(-12, 13, (height, width, 3), dtype=np.int16)
    blended = np.clip(base + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(blended, mode="RGB")

def draw_divider(draw: ImageDraw.ImageDraw, y: int, width: int, color: Tuple[int, int, int]):
    """Draws an elegant gothic horizontal divider with a center diamond."""
    center_x = width // 2
    span = 260
    draw.line([(center_x - span, y), (center_x - 18, y)], fill=color, width=1)
    draw.line([(center_x + 18, y), (center_x + span, y)], fill=color, width=1)

    # Center diamond
    draw.polygon([
        (center_x, y - 5),
        (center_x + 7, y),
        (center_x, y + 5),
        (center_x - 7, y)
    ], fill=color)

def generate_invitation_card(
    guest_name: str,
    role: str,
    serial_number: int,
    soul_pin: Optional[str] = None
) -> io.BytesIO:
    """
    Generates a high-resolution (1080x1350) gothic invitation card
    using the user's custom background artwork.
    """
    width = config.CARD_WIDTH
    height = config.CARD_HEIGHT

    # Initialize canvas
    image = prepare_background(width, height)
    draw = ImageDraw.Draw(image)

    # Fonts
    font_bold = config.FONT_VAZIR_BOLD
    font_reg = config.FONT_VAZIR_REGULAR

    font_sub = get_font(font_bold, 30)
    font_header_en = get_font(font_bold, 42)
    font_header_fa = get_font(font_bold, 50)
    font_name = get_font(font_bold, 62)
    font_role = get_font(font_bold, 40)
    font_subrole = get_font(font_bold, 28)
    font_note = get_font(font_reg, 26)
    font_pin = get_font(font_bold, 30)
    font_timeline = get_font(font_reg, 25)
    font_serial = get_font(font_bold, 36)

    # Palette
    gold = (212, 175, 80)
    silver = (220, 220, 220)
    blood_red = (235, 45, 45)
    crimson = (150, 25, 25)
    blonde_pink = (255, 125, 165)
    dim_white = (195, 195, 205)

    # Text starts below the haunted mansion gates (around Y=400)
    y = 405

    # 1. Main Titles
    draw_centered_text(draw, "PROJECT BLACKOUT", y, font_header_en, silver, width, is_persian=False)
    y += 58

    draw_centered_text(draw, "مهمانی باغ سرهنگ", y, font_header_fa, gold, width, is_persian=True)
    y += 75

    # Divider
    draw_divider(draw, y, width, crimson)
    y += 45

    # 2. Guest Name Frame (Semi-transparent dark glass)
    name_display = guest_name.strip()
    name_box_top = y
    name_box_height = 92
    name_box_margin = 160
    draw.rounded_rectangle(
        [(name_box_margin, name_box_top), (width - name_box_margin, name_box_top + name_box_height)],
        radius=16,
        fill=(18, 10, 14, 210),
        outline=gold,
        width=2
    )
    draw_centered_text(draw, name_display, name_box_top + 14, font_name, (255, 255, 255), width, is_persian=True)
    y = name_box_top + name_box_height + 40

    # Divider
    draw_divider(draw, y, width, gold)
    y += 38

    # 3. Role and Assignment Details
    if role == "role_player":
        draw_centered_text(draw, "نقش: بازیکن طلسم", y, font_role, blood_red, width, is_persian=True)
        y += 50
        draw_centered_text(draw, "THE HUNTER'S PREY", y, font_subrole, (240, 90, 90), width, is_persian=False)
        y += 48
        draw_centered_text(draw, "⚠️ طومار و ماموریت مخفی: در ربات تلگرام (ساعت ۱۹:۳۰)", y, font_note, (255, 205, 205), width, is_persian=True)
        y += 40
        draw_centered_text(draw, "ماموریت: بقا، کشف طلسم‌ها و نجات از دست ۳ تسخیرشده", y, font_note, dim_white, width, is_persian=True)
    else:
        draw_centered_text(draw, "نقش: بلوند بی‌گناه", y, font_role, blonde_pink, width, is_persian=True)
        y += 50
        draw_centered_text(draw, "INNOCENT BLONDE — SAFE ZONE VIP", y, font_subrole, gold, width, is_persian=False)
        y += 48
        draw_centered_text(draw, "🛡 دارای مصونیت مطلق از شکار و تاریکی باغ.", y, font_note, (255, 220, 235), width, is_persian=True)
        y += 40
        draw_centered_text(draw, "پناهگاه سالن گرم: فیلم، نوشیدنی، موسیقی و تماشاچی بازی", y, font_note, dim_white, width, is_persian=True)

    y += 55

    # 4. Secret Soul PIN Code (Used for hunting & immunity verification)
    pin_code = soul_pin or f"{(serial_number * 17 + 103) % 900 + 100}"
    draw_centered_text(draw, f"کد روح شما: {pin_code}", y, font_pin, (255, 215, 0), width, is_persian=True)
    y += 48

    draw_divider(draw, y, width, crimson)
    y += 38

    # 5. Timeline Footer
    draw_centered_text(draw, "۲۹ اکتبر | حرکت: ۱۸:۰۰ | ورود به عمارت: ۱۸:۴۵ | خاموشی: ۲۴:۰۰", y, font_timeline, silver, width, is_persian=True)
    y += 55

    # 6. Unique Serial Code Badge (SOUL-#01)
    serial_str = f"SOUL - #{serial_number:02d}"
    badge_w = 300
    badge_h = 56
    bx = (width - badge_w) // 2
    by = y
    draw.rounded_rectangle(
        [(bx, by), (bx + badge_w, by + badge_h)],
        radius=12,
        fill=(14, 8, 12, 220),
        outline=crimson,
        width=2
    )
    draw_centered_text(draw, serial_str, by + 8, font_serial, gold, width, is_persian=False)

    # Export to BytesIO
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer

def generate_immunity_card(
    guest_name: str,
    soul_pin: str
) -> io.BytesIO:
    """
    Generates a bright, luminous green full-screen (1080x1920) digital immunity shield
    that players can show on their phones to prove immunity from stickers.
    """
    width = 1080
    height = 1920

    # Luminous dark green gradient / radial base
    image = Image.new("RGB", (width, height), (5, 25, 12))
    draw = ImageDraw.Draw(image)

    # Glowing green borders and ornaments
    neon_green = (0, 255, 128)
    emerald = (10, 200, 90)
    bright_text = (220, 255, 230)
    gold = (255, 215, 80)

    # Decorative border inset
    draw.rectangle([(25, 25), (width - 25, height - 25)], outline=neon_green, width=6)
    draw.rectangle([(45, 45), (width - 45, height - 45)], outline=emerald, width=2)

    # Corner brackets / ornaments
    corner_len = 80
    for cx, cy, dx, dy in [
        (25, 25, 1, 1),
        (width - 25, 25, -1, 1),
        (25, height - 25, 1, -1),
        (width - 25, height - 25, -1, -1)
    ]:
        draw.line([(cx, cy), (cx + dx * corner_len, cy)], fill=(255, 255, 255), width=8)
        draw.line([(cx, cy), (cx, cy + dy * corner_len)], fill=(255, 255, 255), width=8)

    font_bold = config.FONT_VAZIR_BOLD
    font_title_en = get_font(font_bold, 44)
    font_title_fa = get_font(font_bold, 64)
    font_name = get_font(font_bold, 72)
    font_badge = get_font(font_bold, 42)
    font_body = get_font(font_bold, 34)
    font_pin = get_font(font_bold, 48)

    y = 180

    # Title English
    draw_centered_text(draw, "IMMUNITY SHIELD ACTIVE", y, font_title_en, neon_green, width, is_persian=False)
    y += 70

    # Title Persian
    draw_centered_text(draw, "🛡 طلسم مصونیت فعال شد 🛡", y, font_title_fa, (255, 255, 255), width, is_persian=True)
    y += 110

    draw_divider(draw, y, width, neon_green)
    y += 80

    # Shield polygon badge
    center_x = width // 2
    shield_pts = [
        (center_x - 140, y),
        (center_x + 140, y),
        (center_x + 140, y + 160),
        (center_x, y + 260),
        (center_x - 140, y + 160)
    ]
    draw.polygon(shield_pts, fill=(15, 65, 30), outline=neon_green, width=5)
    # Inner shield symbol
    draw_centered_text(draw, "SAFE", y + 80, font_badge, (255, 255, 255), width, is_persian=False)
    draw_centered_text(draw, "مصون", y + 145, font_badge, neon_green, width, is_persian=True)
    y += 330

    # Name box
    name_box_top = y
    name_box_height = 130
    name_margin = 100
    draw.rounded_rectangle(
        [(name_margin, name_box_top), (width - name_margin, name_box_top + name_box_height)],
        radius=20,
        fill=(12, 50, 24),
        outline=neon_green,
        width=3
    )
    draw_centered_text(draw, guest_name.strip(), name_box_top + 25, font_name, (255, 255, 255), width, is_persian=True)
    y = name_box_top + name_box_height + 70

    # Pin & Soul
    draw_centered_text(draw, f"کد روح: {soul_pin}", y, font_pin, gold, width, is_persian=True)
    y += 90

    draw_divider(draw, y, width, neon_green)
    y += 80

    # Rules / Warning
    draw_centered_text(draw, "⛔️ غیرقابل تسخیر تا پایان مهمانی ⛔️", y, font_body, (255, 90, 90), width, is_persian=True)
    y += 80

    draw_centered_text(draw, "این صفحه را به صورت تمام‌صفحه به افراد تسخیرشده نشان دهید.", y, font_body, bright_text, width, is_persian=True)
    y += 65

    draw_centered_text(draw, "هیچ تسخیرشده‌ای حق چسباندن استیکر به شما را ندارد!", y, font_body, neon_green, width, is_persian=True)
    y += 100

    draw_divider(draw, y, width, emerald)
    y += 80

    draw_centered_text(draw, "باغ سرهنگ — شب ۲۹ اکتبر", y, font_badge, (160, 210, 180), width, is_persian=True)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer

