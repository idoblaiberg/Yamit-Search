#!/usr/bin/env python3
"""
build_prices.py — run once to build prices.json from yamitysb.co.il
Fetches all ~2,690 product pages across 3 sitemaps, extracts JSON-LD prices.
Output: prices.json committed to repo, loaded by index.html at startup.
"""

import urllib.request, re, json, time, threading
from queue import Queue

SITEMAPS = [
    'https://yamitysb.co.il/product-sitemap.xml',
    'https://yamitysb.co.il/product-sitemap2.xml',
    'https://yamitysb.co.il/product-sitemap3.xml',
]
HEADERS = {'User-Agent': 'Mozilla/5.0 (build_prices/1.0)'}
THREADS = 5
DELAY   = 0.3   # seconds between requests per thread
OUT     = 'prices.json'

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')

def make_key(name):
    """Extract English letter-words (2+ chars), lowercase, joined by space."""
    words = re.findall(r'[A-Za-z]{2,}', name)
    return ' '.join(w.lower() for w in words) if words else None

def extract_price(html):
    """Return (name, low, high) from product page JSON-LD, or (None,None,None)."""
    blocks = re.findall(r'<script[^>]+ld\+json[^>]*>(.*?)</script>', html, re.DOTALL|re.IGNORECASE)
    for block in blocks:
        try:
            obj = json.loads(block)
            items = obj.get('@graph', [obj])
            for item in items:
                if not isinstance(item, dict): continue
                if item.get('@type') != 'Product': continue
                name = item.get('name', '')
                url  = item.get('url', '')
                low = high = None
                offers = item.get('offers', {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                otype = offers.get('@type', '')
                if otype == 'AggregateOffer':
                    lp = offers.get('lowPrice')
                    hp = offers.get('highPrice')
                    if lp is not None: low  = float(lp)
                    if hp is not None: high = float(hp)
                elif otype == 'Offer':
                    p = offers.get('price')
                    if p is not None: low = high = float(p)
                return name, url, low, high
        except Exception:
            pass
    return None, None, None, None

def collect_urls():
    urls = []
    for sm in SITEMAPS:
        try:
            xml = fetch(sm)
            locs = re.findall(r'<loc>(.*?)</loc>', xml)
            # Only product URLs (not /shop/ or category pages)
            locs = [l for l in locs if '/product/' in l and '/product-category/' not in l and l.rstrip('/') != 'https://yamitysb.co.il/shop']
            print(f'  {sm.split("/")[-1]}: {len(locs)} products')
            urls.extend(locs)
        except Exception as e:
            print(f'  ERROR fetching {sm}: {e}')
    return urls

def worker(q, results, lock, counter, total):
    while True:
        url = q.get()
        if url is None:
            break
        try:
            html = fetch(url)
            name, prod_url, low, high = extract_price(html)
            if name:
                key = make_key(name)
                if key:
                    with lock:
                        results[key] = {
                            'name': name,
                            'url':  prod_url or url,
                            'low':  low,
                            'high': high,
                        }
        except Exception as e:
            pass  # Skip failed pages silently
        finally:
            with lock:
                counter[0] += 1
                done = counter[0]
            if done % 50 == 0 or done == total:
                print(f'  {done}/{total} pages processed...')
            time.sleep(DELAY)
            q.task_done()

def main():
    print('Collecting product URLs from sitemaps...')
    urls = collect_urls()
    total = len(urls)
    print(f'Total: {total} product URLs\n')

    results = {}
    lock = threading.Lock()
    counter = [0]

    q = Queue()
    for url in urls:
        q.put(url)

    print(f'Scraping with {THREADS} threads at {DELAY}s delay each...')
    threads = []
    for _ in range(THREADS):
        t = threading.Thread(target=worker, args=(q, results, lock, counter, total))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.1)  # stagger thread starts

    # Add sentinel values to stop threads
    for _ in range(THREADS):
        q.put(None)

    q.join()

    print(f'\nDone! {len(results)} entries extracted.')
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    size_kb = len(json.dumps(results, ensure_ascii=False).encode('utf-8')) / 1024
    priced  = sum(1 for v in results.values() if v['low'] is not None)
    print(f'Saved {OUT}: {size_kb:.0f} KB, {priced} entries with prices, {len(results)-priced} without.')

if __name__ == '__main__':
    main()
