import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0"))
PLAYER_CAP: int = int(os.getenv("PLAYER_CAP", "15"))
DB_PATH: Path = BASE_DIR / os.getenv("DB_PATH", "colonel_party.db")

ASSETS_DIR: Path = BASE_DIR / "assets"
FONTS_DIR: Path = ASSETS_DIR / "fonts"
IMAGES_DIR: Path = ASSETS_DIR / "images"

FONT_VAZIR_BOLD: Path = FONTS_DIR / "Vazirmatn-Bold.ttf"
FONT_VAZIR_REGULAR: Path = FONTS_DIR / "Vazirmatn-Regular.ttf"

if (IMAGES_DIR / "card_bg.jpg").exists():
    CARD_BG_PATH: Path = IMAGES_DIR / "card_bg.jpg"
else:
    CARD_BG_PATH: Path = IMAGES_DIR / "card_bg.png"

CARD_WIDTH: int = 1080
CARD_HEIGHT: int = 1350
