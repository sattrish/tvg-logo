import os
import re
import requests
from PIL import Image, ImageDraw
from io import BytesIO

PLAYLISTS = {
    "z5": "https://raw.githubusercontent.com/alex4528y/m3u/refs/heads/main/z5.m3u",
    "jstar": "https://raw.githubusercontent.com/alex4528y/m3u/refs/heads/main/jstar.m3u"
}

BASE_DIR = "images/tvg-logo"


def make_round_logo(img):
    size = (512, 512)
    img = img.resize(size).convert("RGBA")

    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)

    bg = Image.new("RGBA", size, (255, 255, 255, 255))
    bg.paste(img, (0, 0), mask)

    return bg


def clean_name(name):
    return re.sub(r'[^a-zA-Z0-9_\- ]', '', name).strip()


for name, url in PLAYLISTS.items():
    print(f"Processing: {name}")

    folder = os.path.join(BASE_DIR, name)
    os.makedirs(folder, exist_ok=True)

    res = requests.get(url)
    lines = res.text.splitlines()

    for line in lines:
        if "#EXTINF" in line:
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            name_match = re.search(r',(.+)', line)

            if logo_match and name_match:
                logo_url = logo_match.group(1)
                channel_name = clean_name(name_match.group(1))

                try:
                    img_res = requests.get(logo_url, timeout=10)
                    img = Image.open(BytesIO(img_res.content))

                    img = make_round_logo(img)

                    save_path = os.path.join(folder, f"{channel_name}.png")
                    img.save(save_path)

                    print(f"Saved: {channel_name}")

                except Exception as e:
                    print(f"Failed: {channel_name} -> {e}")
