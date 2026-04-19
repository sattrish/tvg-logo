import os
import requests
import hashlib
import json
import re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
from io import BytesIO
from urllib.parse import urljoin

BASE = "https://tulnit.com"
HOME = BASE + "/"

SAVE_DIR = "tvg-logo"
JSON_FILE = "logos.json"

os.makedirs(SAVE_DIR, exist_ok=True)

downloaded_hashes = set()
logo_map = {}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# 🔐 hash
def get_hash(content):
    return hashlib.md5(content).hexdigest()

# 📂 get categories
def get_categories():
    print("Fetching categories...")
    res = requests.get(HOME, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    categories = {}

    for a in soup.select("ul.sub-menu a, .main-header a"):
        href = a.get("href")
        name = a.text.strip()

        if href and "/channel/" in href:
            full_url = urljoin(BASE, href)

            if full_url not in categories.values():
                categories[name] = full_url

    print(f"Total categories: {len(categories)}")
    return categories

# 🔢 get total pages from "Page 1 of X"
def get_total_pages(soup):
    el = soup.select_one(".pagination span")
    if el:
        match = re.search(r'of (\d+)', el.text)
        if match:
            return int(match.group(1))
    return 1

# 🔗 generate all page links
def get_all_pages(base_url, total):
    urls = [base_url]
    for i in range(2, total + 1):
        urls.append(f"{base_url}page/{i}/")
    return urls

# 🖼️ scrape images
def scrape_page(url):
    print(f"Scraping: {url}")
    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    images = []
    for img in soup.select("article .poster img"):
        src = img.get("src")
        name = img.get("alt", "logo").strip().replace(" ", "-").lower()
        if src:
            images.append((src, name))

    return images, soup

# 🎨 process image
def process_image(url, name):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        content = res.content

        # duplicate check
        h = get_hash(content)
        if h in downloaded_hashes:
            print("Duplicate skipped")
            return None
        downloaded_hashes.add(h)

        img = Image.open(BytesIO(content)).convert("RGBA")

        # square crop
        w, h = img.size
        m = min(w, h)
        img = img.crop(((w - m)//2, (h - m)//2, (w + m)//2, (h + m)//2))

        # resize
        img = img.resize((512, 512))

        # round mask
        mask = Image.new("L", (512, 512), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 512, 512), fill=255)
        img.putalpha(mask)

        filename = f"{name}.png"
        path = os.path.join(SAVE_DIR, filename)
        img.save(path, "PNG")

        print(f"Saved: {filename}")
        return filename

    except Exception as e:
        print("Error:", e)
        return None

# 🚀 crawl category
def crawl_category(cat_name, url):
    print(f"\n=== {cat_name} ===")

    logo_map[cat_name] = {}

    # first page load
    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    total_pages = get_total_pages(soup)
    print(f"Total pages: {total_pages}")

    page_links = get_all_pages(url, total_pages)

    for page in page_links:
        images, _ = scrape_page(page)

        for img_url, name in images:
            filename = process_image(img_url, name)
            if filename:
                logo_map[cat_name][name] = f"{SAVE_DIR}/{filename}"

# 💾 save json
def save_json():
    with open(JSON_FILE, "w") as f:
        json.dump(logo_map, f, indent=2)
    print("\nJSON saved")

# ▶️ main
def main():
    categories = get_categories()

    for name, url in categories.items():
        crawl_category(name, url)

    save_json()

if __name__ == "__main__":
    main()
