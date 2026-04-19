import os
import requests
import hashlib
import json
import re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
from io import BytesIO
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://tulnit.com"
HOME = BASE + "/"

SAVE_DIR = "tvg-logo"
JSON_FILE = "logos.json"

os.makedirs(SAVE_DIR, exist_ok=True)

session = requests.Session()
HEADERS = {"User-Agent": "Mozilla/5.0"}

MAX_THREADS = 15  # ⚡ speed control (10–20 best)

downloaded_hashes = set()
logo_map = {}

# 🔐 hash
def get_hash(content):
    return hashlib.md5(content).hexdigest()

# 🧹 clean name
def slugify(text):
    return text.strip().lower().replace(" ", "-")

# 📂 get categories
def get_categories():
    res = session.get(HOME, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    categories = {}

    for a in soup.select("ul.sub-menu a, .main-header a"):
        href = a.get("href")
        name = a.text.strip()

        if href and "/channel/" in href:
            full_url = urljoin(BASE, href)

            if full_url not in categories.values():
                categories[name] = full_url

    print(f"Categories: {len(categories)}")
    return categories

# 🔢 total pages detect
def get_total_pages(soup):
    el = soup.select_one(".pagination span")
    if el:
        match = re.search(r'of (\d+)', el.text)
        if match:
            return int(match.group(1))
    return 1

# 🔗 generate pages
def get_all_pages(base_url, total):
    return [base_url] + [f"{base_url}page/{i}/" for i in range(2, total+1)]

# 🖼️ scrape images
def scrape_page(url):
    try:
        res = session.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        images = []
        for img in soup.select("article .poster img"):
            src = img.get("src")
            name = img.get("alt", "logo").strip().replace(" ", "-").lower()
            if src:
                images.append((src, name))

        return images, soup
    except:
        return [], None

# 🎨 process image
def process_image(url, name, category_folder):
    try:
        filename = f"{name}.png"
        folder_path = os.path.join(SAVE_DIR, category_folder)
        os.makedirs(folder_path, exist_ok=True)

        path = os.path.join(folder_path, filename)

        # ⚡ skip existing
        if os.path.exists(path):
            return (name, path)

        res = session.get(url, headers=HEADERS, timeout=10)
        content = res.content

        # duplicate
        h = get_hash(content)
        if h in downloaded_hashes:
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

        img.save(path, "PNG")

        print("Saved:", path)
        return (name, path)

    except Exception as e:
        print("Error:", e)
        return None

# ⚡ parallel processing
def process_images_parallel(images, category_folder):
    results = []

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [
            executor.submit(process_image, img_url, name, category_folder)
            for img_url, name in images
        ]

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    return results

# 🚀 crawl category
def crawl_category(cat_name, url):
    print(f"\n=== {cat_name} ===")

    cat_slug = slugify(cat_name)
    logo_map[cat_slug] = {}

    images, soup = scrape_page(url)
    if not soup:
        return

    total_pages = get_total_pages(soup)
    print(f"Pages: {total_pages}")

    pages = get_all_pages(url, total_pages)

    for page in pages:
        images, _ = scrape_page(page)

        results = process_images_parallel(images, cat_slug)

        for name, path in results:
            logo_map[cat_slug][name] = path

# 💾 save JSON
def save_json():
    with open(JSON_FILE, "w") as f:
        json.dump(logo_map, f, indent=2)

# ▶️ main
def main():
    categories = get_categories()

    for name, url in categories.items():
        crawl_category(name, url)

    save_json()
    print("\nDone ✅")

if __name__ == "__main__":
    main()
