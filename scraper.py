#!/usr/bin/env python3
"""
yamit_scraper.py — Scrape yamitysb.co.il product catalog
Outputs: yamit_inventory.json  (compatible with the Yamit Search app)

Usage:
    python3 scraper.py
    python3 scraper.py --out my_inventory.json
    python3 scraper.py --pages 5          # limit to 5 pages per category
    python3 scraper.py --delay 1.5        # seconds between requests (be polite)

The JSON file can then be loaded into the Yamit Search app via "טעינת מלאי".
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser

BASE_URL = "https://yamitysb.co.il"

# WooCommerce category slugs → Hebrew category label
CATEGORIES = {
    "kites":            "קייט",
    "kite-boards":      "קייט",
    "bars-lines":       "קייט",
    "harnesses":        "קייט",
    "windsurf-sails":   "גלישת רוח",
    "windsurf-boards":  "גלישת רוח",
    "windsurf-masts":   "גלישת רוח",
    "windsurf-booms":   "גלישת רוח",
    "wing-foil":        "ווינג",
    "wing-foil-boards": "ווינג",
    "foils":            "ווינג",
    "kayaks":           "קיאק",
    "sup":              "SUP",
    "accessories":      "אביזרים",
    "wetsuits":         "חליפות",
    "safety":           "בטיחות",
}


# ── Minimal HTML parser to extract product cards ─────────────────────────────

class ProductParser(HTMLParser):
    """Extract product info from a WooCommerce shop page."""

    def __init__(self):
        super().__init__()
        self.products = []
        self._in_product = False
        self._in_title = False
        self._in_price = False
        self._in_sku = False
        self._depth = 0
        self._product_depth = 0
        self._cur = {}
        self._text_buf = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        cls = attrs.get("class", "")

        # Product article / li container
        if tag in ("li", "article") and "product" in cls and "type-product" in cls:
            self._in_product = True
            self._product_depth = self._depth
            self._cur = {"name": "", "url": "", "price": "", "in_stock": True}

        if self._in_product:
            # Product link + name
            if tag == "a" and "woocommerce-loop-product__link" in cls:
                self._cur["url"] = attrs.get("href", "")
            if tag in ("h2", "h3") and "woocommerce-loop-product__title" in cls:
                self._in_title = True
                self._text_buf = ""
            # Price
            if tag == "span" and "woocommerce-Price-amount" in cls:
                self._in_price = True
                self._text_buf = ""
            # Out-of-stock badge
            if tag == "span" and "out-of-stock" in cls.lower():
                self._cur["in_stock"] = False
            if tag == "p" and "out-of-stock" in cls.lower():
                self._cur["in_stock"] = False

        self._depth += 1

    def handle_endtag(self, tag):
        self._depth -= 1

        if self._in_title and tag in ("h2", "h3"):
            self._cur["name"] = self._text_buf.strip()
            self._in_title = False

        if self._in_price and tag == "span":
            if not self._cur.get("price"):
                self._cur["price"] = self._text_buf.strip()
            self._in_price = False

        if self._in_product and self._depth == self._product_depth:
            if self._cur.get("name"):
                self.products.append(self._cur)
            self._in_product = False
            self._cur = {}

    def handle_data(self, data):
        if self._in_title or self._in_price:
            self._text_buf += data


class PaginationParser(HTMLParser):
    """Find the last page number on a shop page."""

    def __init__(self):
        super().__init__()
        self.max_page = 1

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs = dict(attrs)
            cls = attrs.get("class", "")
            href = attrs.get("href", "")
            if "page-numbers" in cls and href:
                m = re.search(r'/page/(\d+)', href)
                if m:
                    self.max_page = max(self.max_page, int(m.group(1)))


# ── HTTP helpers ──────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; YamitSearchBot/1.0; "
        "+https://github.com/idoblaiberg/Yamit-Search)"
    ),
    "Accept-Language": "he,en-US;q=0.9,en;q=0.8",
}


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = "utf-8"
            ct = resp.headers.get_content_charset()
            if ct:
                charset = ct
            return resp.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return None


# ── SKU extraction helpers ────────────────────────────────────────────────────

_SIZES = re.compile(r'\b(\d{1,2}(?:[.,]\d)?(?:m)?)\b')
_MODEL = re.compile(r'\b([A-Z][A-Z0-9\-]{2,})\b')


def guess_sku(name, cat_label):
    """Generate a best-effort SKU from the product name."""
    # Extract uppercase model tokens + numeric size
    models = _MODEL.findall(name)
    sizes  = _SIZES.findall(name)
    parts  = models[:2] + sizes[:1]
    if parts:
        return "-".join(parts)
    # Fallback: first 3 words
    words = name.split()[:3]
    return "-".join(w[:6].upper() for w in words if w)


def strip_hebrew(s):
    """Remove Hebrew characters, keep Latin + digits + spaces."""
    return re.sub(r'[\u0590-\u05FF]+', '', s).strip()


# ── Scraper core ──────────────────────────────────────────────────────────────

def scrape_category(slug, cat_label, max_pages, delay):
    """Return list of raw product dicts for one category."""
    products = []
    base = f"{BASE_URL}/product-category/{slug}/"

    # Discover page count
    html = fetch(base)
    if html is None:
        return products

    pag = PaginationParser()
    pag.feed(html)
    total_pages = min(pag.max_page, max_pages)

    # Parse page 1
    p = ProductParser()
    p.feed(html)
    products.extend(p.products)
    print(f"  {slug}: page 1/{total_pages} — {len(p.products)} products")

    for page in range(2, total_pages + 1):
        time.sleep(delay)
        url = f"{base}page/{page}/"
        html = fetch(url)
        if not html:
            break
        p = ProductParser()
        p.feed(html)
        products.extend(p.products)
        print(f"  {slug}: page {page}/{total_pages} — {len(p.products)} products")

    return products


def build_inventory_item(raw, cat_label):
    """Convert a raw scraped product to the Yamit Search INV schema."""
    name = raw.get("name", "").strip()
    if not name:
        return None

    sku = guess_sku(name, cat_label)
    alt = strip_hebrew(name)        # Latin/numeric portion as alternate name
    if alt == name:
        alt = ""

    price_str = raw.get("price", "")
    price_num = 0.0
    if price_str:
        digits = re.sub(r'[^\d.]', '', price_str)
        try:
            price_num = float(digits)
        except ValueError:
            pass

    return {
        "name":     name,
        "sku":      sku,
        "alt":      alt,
        "cat":      cat_label,
        "qty":      1 if raw.get("in_stock", True) else 0,
        "in_stock": raw.get("in_stock", True),
        "price":    price_num,
        "url":      raw.get("url", ""),
    }


def scrape_all(max_pages, delay):
    all_items = []
    seen_names = set()

    for slug, cat_label in CATEGORIES.items():
        print(f"\nCategory: {slug} → {cat_label}")
        raw_products = scrape_category(slug, cat_label, max_pages, delay)
        time.sleep(delay)

        for raw in raw_products:
            item = build_inventory_item(raw, cat_label)
            if item is None:
                continue
            key = item["name"].lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            all_items.append(item)

    return all_items


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrape yamitysb.co.il inventory")
    parser.add_argument("--out",   default="yamit_inventory.json",
                        help="Output JSON file path (default: yamit_inventory.json)")
    parser.add_argument("--pages", type=int, default=20,
                        help="Max pages per category (default: 20)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds between requests (default: 1.0)")
    args = parser.parse_args()

    print(f"Scraping {BASE_URL}")
    print(f"Max pages per category: {args.pages}, delay: {args.delay}s")

    items = scrape_all(max_pages=args.pages, delay=args.delay)

    in_stock_count = sum(1 for x in items if x["in_stock"])
    print(f"\nTotal unique products: {len(items)}")
    print(f"In stock: {in_stock_count}")

    output = {
        "source":    BASE_URL,
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "count":     len(items),
        "items":     items,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Saved → {args.out}")


if __name__ == "__main__":
    main()
