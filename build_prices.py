#!/usr/bin/env python3
"""
build_prices.py — run once to build prices.json from yamitysb.co.il
Fetches all ~2,690 product pages across 3 sitemaps, extracts JSON-LD prices.
Output: prices.json committed to repo, loaded by index.html at startup.

Usage:
    python3 build_prices.py          # fresh run or auto-resume from checkpoint
    python3 build_prices.py --fresh  # ignore checkpoint, start over

Resume: if killed, re-run same command — resumes from checkpoint automatically.
"""

import urllib.request
import urllib.error
import re
import json
import time
import threading
import logging
import os
import html
import sys
from queue import Queue
from datetime import date

# ── Configuration ────────────────────────────────────────────────────────────
SITEMAPS = [
    'https://yamitysb.co.il/product-sitemap.xml',
    'https://yamitysb.co.il/product-sitemap2.xml',
    'https://yamitysb.co.il/product-sitemap3.xml',
]
HEADERS       = {'User-Agent': 'Mozilla/5.0 (build_prices/2.0)'}
THREADS       = 5
DELAY         = 0.2    # seconds between requests per thread
OUT           = 'prices.json'
PROGRESS_FILE = 'prices_progress.json'
LOG_FILE      = 'build_prices.log'
SAVE_EVERY    = 100

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
    ]
)
log = logging.getLogger('build_prices')

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch(url, timeout=8):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='replace')


def make_key(name):
    """
    Extract English letter-words (2+ chars) from name, lowercase, joined by space.
    Quality gate: a single word must be 3+ chars; two or more words of any length pass.
    Examples:
      "דאוטון קייט EVO SLS 2026" → "evo sls"
      "מפסק HD"                  → None  (single 2-char word, rejected)
      "P&H SCORPIO"              → "ph scorpio"  (after html.unescape)
    """
    words = re.findall(r'[A-Za-z]{2,}', name)
    if not words:
        return None
    key_words = [w.lower() for w in words]
    # Reject weak single-word keys like "hd", "ss", "wc"
    if len(key_words) == 1 and len(key_words[0]) < 3:
        return None
    return ' '.join(key_words)


def extract_price(page_html):
    """
    Return (name, url, low, high) from product page JSON-LD.
    Returns (None, None, None, None) if no Product found.
    Handles both AggregateOffer (lowPrice/highPrice) and single Offer (price).
    """
    blocks = re.findall(
        r'<script[^>]+ld\+json[^>]*>(.*?)</script>',
        page_html, re.DOTALL | re.IGNORECASE
    )
    for block in blocks:
        try:
            obj = json.loads(block)
            items = obj.get('@graph', [obj])
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get('@type') != 'Product':
                    continue
                name     = item.get('name', '')
                prod_url = item.get('url', '')
                low = high = None
                offers = item.get('offers', {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                otype = offers.get('@type', '')
                if otype == 'AggregateOffer':
                    lp = offers.get('lowPrice')
                    hp = offers.get('highPrice')
                    if lp is not None:
                        low  = float(lp)
                    if hp is not None:
                        high = float(hp)
                elif otype == 'Offer':
                    p = offers.get('price')
                    if p is not None:
                        low = high = float(p)
                return name, prod_url, low, high
        except Exception:
            pass
    return None, None, None, None


def collect_urls():
    """Fetch all 3 sitemaps, deduplicate, return list of product URLs."""
    seen = set()
    urls = []
    for sm in SITEMAPS:
        try:
            xml  = fetch(sm, timeout=30)
            locs = re.findall(r'<loc>(.*?)</loc>', xml)
            locs = [
                l for l in locs
                if '/product/' in l
                and '/product-category/' not in l
                and l.rstrip('/') != 'https://yamitysb.co.il/shop'
            ]
            before = len(locs)
            locs   = [l for l in locs if l not in seen]
            seen.update(locs)
            urls.extend(locs)
            dupes = before - len(locs)
            note  = f' ({dupes} dupes skipped)' if dupes else ''
            print(f'  {sm.split("/")[-1]}: {len(locs)} unique products{note}')
        except Exception as e:
            log.error('ERROR fetching sitemap %s: %s', sm, e)
    return urls


def write_prices_json(results, total_urls):
    """Write prices.json with _meta header."""
    priced = sum(1 for v in results.values() if isinstance(v, dict) and v.get('low') is not None)
    output = {
        '_meta': {
            'generated': date.today().isoformat(),
            'total':     total_urls,
            'matched':   len(results),
            'priced':    priced,
        }
    }
    output.update(results)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def worker(q, results, processed_set, lock, counter, total, start_time):
    while True:
        url = q.get()
        if url is None:
            break
        try:
            page_html = fetch(url)
            name, prod_url, low, high = extract_price(page_html)
            if name:
                name = html.unescape(name)   # fix &amp; &quot; etc.
                key  = make_key(name)
                if key:
                    with lock:
                        results[key] = {
                            'name': name,
                            'url':  prod_url or url,
                            'low':  low,
                            'high': high,
                        }
                else:
                    log.debug('No valid key for: %s', name)
            else:
                log.debug('No JSON-LD Product at: %s', url)
        except urllib.error.HTTPError as e:
            log.warning('HTTP %s: %s', e.code, url)
        except urllib.error.URLError as e:
            log.warning('URLError %s: %s', e.reason, url)
        except Exception as e:
            log.warning('Failed %s: %s', url, e)
        finally:
            with lock:
                processed_set.add(url)
                counter[0] += 1
                done    = counter[0]
                elapsed = time.time() - start_time
                rate    = done / elapsed if elapsed > 0 else 1
                eta_s   = (total - done) / rate if rate > 0 else 0
                priced  = sum(1 for v in results.values() if isinstance(v, dict) and v.get('low') is not None)
                line = (f'\r  {done}/{total} | {len(results)} entries ({priced} priced)'
                        f' | {elapsed:.0f}s elapsed | ETA {eta_s:.0f}s    ')
                print(line, end='', flush=True)
                if done % SAVE_EVERY == 0 or done == total:
                    # Incremental save: both checkpoint and prices.json
                    checkpoint = {
                        'processed': list(processed_set),
                        'results':   results,
                    }
                    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(checkpoint, f, ensure_ascii=False)
                    write_prices_json(results, total)
                    print()  # newline after progress line
                    print(f'  Saved checkpoint: {done} processed, {len(results)} entries', flush=True)
            time.sleep(DELAY)
            q.task_done()


def main():
    fresh = '--fresh' in sys.argv

    # ── Resume or fresh start ─────────────────────────────────────────────────
    processed_urls = set()
    results        = {}
    if not fresh and os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, encoding='utf-8') as f:
                saved = json.load(f)
            processed_urls = set(saved.get('processed', []))
            results        = saved.get('results', {})
            print(f'Resuming from checkpoint: {len(processed_urls)} URLs already done, '
                  f'{len(results)} entries loaded.')
        except Exception as e:
            print(f'Could not load checkpoint ({e}), starting fresh.')
            processed_urls = set()
            results        = {}
    elif fresh:
        print('--fresh flag: ignoring any existing checkpoint.')

    # ── Collect URLs ──────────────────────────────────────────────────────────
    print('Collecting product URLs from sitemaps...')
    all_urls = collect_urls()
    total    = len(all_urls)
    print(f'Total unique: {total} product URLs')

    urls_to_process = [u for u in all_urls if u not in processed_urls]
    skip_count      = total - len(urls_to_process)
    if skip_count:
        print(f'Skipping {skip_count} already-processed URLs.')
    print(f'Scraping {len(urls_to_process)} URLs with {THREADS} threads at {DELAY}s delay each...\n')

    if not urls_to_process:
        print('Nothing to do — all URLs already processed!')
        write_prices_json(results, total)
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        return

    # ── Spawn workers ─────────────────────────────────────────────────────────
    lock       = threading.Lock()
    counter    = [0]
    start_time = time.time()

    q = Queue()
    for url in urls_to_process:
        q.put(url)
    for _ in range(THREADS):
        q.put(None)  # sentinels

    threads = []
    for _ in range(THREADS):
        t = threading.Thread(
            target=worker,
            args=(q, results, processed_urls, lock, counter, len(urls_to_process), start_time)
        )
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.1)

    q.join()
    print()  # final newline

    # ── Final write + cleanup ─────────────────────────────────────────────────
    write_prices_json(results, total)
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    size_kb = os.path.getsize(OUT) / 1024
    priced  = sum(1 for v in results.values() if isinstance(v, dict) and v.get('low') is not None)
    print(f'\nDone! prices.json: {size_kb:.0f} KB | {len(results)} entries | {priced} with prices | '
          f'{len(results) - priced} order-only/no-price')
    print(f'Check failures: grep -c WARNING {LOG_FILE}')


if __name__ == '__main__':
    main()
