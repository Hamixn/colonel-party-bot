import os
import shutil
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "assets" / "fonts"
IMAGES_DIR = BASE_DIR / "assets" / "images"

FONT_URLS = {
    "Vazirmatn-Bold.ttf": "https://github.com/rastikerdar/vazirmatn/raw/v33.003/fonts/ttf/Vazirmatn-Bold.ttf",
    "Vazirmatn-Regular.ttf": "https://github.com/rastikerdar/vazirmatn/raw/v33.003/fonts/ttf/Vazirmatn-Regular.ttf",
}

def setup():
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    for font_name, url in FONT_URLS.items():
        font_dest = FONTS_DIR / font_name
        if not font_dest.exists():
            print(f"Downloading {font_name}...")
            urllib.request.urlretrieve(url, font_dest)
            print(f"Saved: {font_dest}")
        else:
            print(f"Font already exists: {font_dest}")

if __name__ == "__main__":
    setup()
