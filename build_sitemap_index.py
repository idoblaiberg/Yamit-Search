#!/usr/bin/env python3
"""build_sitemap_index.py — builds sitemap_index.json in ~5 seconds.

Fetches 3 sitemaps, decodes URL slugs into searchable word strings,
saves sitemap_index.json. Used by index.html to find direct product URLs.

Usage:
    python3 build_sitemap_index.py
"""
import urllib.request
import urllib.parse
import re
import json
import os
from datetime import date

SITEMAPS = [
    'https://yamitysb.co.il/product-sitemap.xml',
    'https://yamitysb.co.il/product-sitemap2.xml',
    'https://yamitysb.co.il/product-sitemap3.xml',
]
HEADERS = {'User-Agent': 'Mozilla/5.0 (sitemap_index/1.0)'}
OUT = 'sitemap_index.json'


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')


def slug_to_words(url):
    """Extract decoded slug words from a product URL.

    '/product/evo-sls-2026/'  →  'evo sls 2026'
    '/product/%d7%a7%d7%99%d7%90%d7%a7-scorpio-mkii/' → 'קיאק scorpio mkii'
    """
    m = re.search(r'/product/([^/]+)/?$', url)
    if not m:
        return None
    decoded = urllib.parse.unquote(m.group(1))
    words = re.sub(r'\s+', ' ', decoded.replace('-', ' ').lower().strip())
    return words if words else None


def main():
    seen = set()
    entries = []

    for sm in SITEMAPS:
        try:
            xml = fetch(sm)
            locs = [l for l in re.findall(r'<loc>(.*?)</loc>', xml)
                    if '/product/' in l
                    and '/product-category/' not in l
                    and l.rstrip('/') != 'https://yamitysb.co.il/shop']
            count = 0
            for url in locs:
                if url in seen:
                    continue
                seen.add(url)
                words = slug_to_words(url)
                if words:
                    entries.append([words, url])
                    count += 1
            print(f'  {sm.split("/")[-1]}: {count} products')
        except Exception as e:
            print(f'  ERROR fetching {sm}: {e}')

    output = {
        '_meta': {
            'generated': date.today().isoformat(),
            'count': len(entries),
        },
        'entries': entries,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

    size_kb = os.path.getsize(OUT) // 1024
    print(f'\nDone: {len(entries)} entries, {size_kb}KB → {OUT}')


if __name__ == '__main__':
    main()
