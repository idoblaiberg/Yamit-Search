#!/opt/homebrew/bin/python3
import csv, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

CSV_FILE = Path(__file__).parent / 'yamit_products.csv'
OUT_FILE = Path(__file__).parent / 'product_index.json'

# Column indices (0-based) -- confirmed from CSV header order
C_SPORT, C_CAT, C_NAME = 0, 1, 2
C_ATTR1, C_ATTR2, C_SKU = 3, 4, 5
C_PRICE, C_SALE, C_STOCK, C_URL = 6, 7, 8, 9

AZL = '\u05d0\u05d6\u05dc'  # Hebrew "sold out"

SPORT_SYNONYMS = {
    '\u05d2\u05dc\u05d9\u05e9\u05ea \u05e1\u05d0\u05e4': ['fanatic', 'quickblade', 'qb'],
    '\u05e7\u05d9\u05d9\u05d8 \u05e1\u05e8\u05e4\u05d9\u05e0\u05d2': ['duotone', 'ion'],
    '\u05d5\u05d5\u05d9\u05e0\u05d2 \u05e4\u05d5\u05d9\u05dc': ['duotone', 'fanatic', 'ion'],
    '\u05d2\u05dc\u05d9\u05e9\u05d4 \u05e8\u05d5\u05d7': ['duotone', 'fanatic', 'ion'],
    '\u05e7\u05d9\u05d0\u05e7\u05d9\u05dd': ['nelo', 'tiderace', 'braca'],
    '\u05d2\u05dc\u05d9\u05e9\u05ea \u05d2\u05dc\u05d9\u05dd': ['guild', 'stewart', 'piko', 'rusty'],
    '\u05d1\u05d9\u05d2\u05d5\u05d3 \u05d2\u05dc\u05d9\u05e9\u05d4': ["o'neill", 'ion', 'wip'],
}

def parse_price(s):
    s = (s or '').replace(',', '').strip()
    m = re.search(r'\d+', s)
    return int(m.group()) if m else None

def normalize_stock(raw):
    raw = (raw or '').strip()
    return 'in_stock' if raw and AZL not in raw else 'out_of_stock'

def build_search_doc(name, sport, cat, sku, variants):
    parts = [name.lower(), sport.lower(), cat.lower(), (sku or '').lower()]
    parts += [v['size'].lower()  for v in variants if v['size']]
    parts += [v['color'].lower() for v in variants if v['color']]
    for sport_key, synonyms in SPORT_SYNONYMS.items():
        if sport_key in sport:
            parts += synonyms
    return ' '.join(p for p in parts if p)

if not CSV_FILE.exists():
    sys.exit(f'ERROR: {CSV_FILE} not found')

rows = []
with open(CSV_FILE, encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    for row in reader:
        if len(row) > C_NAME and row[C_NAME].strip():
            rows.append(row)
print(f'Read {len(rows)} rows')

groups, order = {}, []
for row in rows:
    key = (row[C_NAME].strip(), row[C_URL].strip())
    if key not in groups:
        groups[key] = []
        order.append(key)
    groups[key].append(row)
print(f'Grouped into {len(order)} products')

products = []
for key in order:
    group = groups[key]
    first = group[0]
    variants, seen = [], set()
    for row in group:
        size  = row[C_ATTR1].strip() if len(row) > C_ATTR1 else ''
        color = row[C_ATTR2].strip() if len(row) > C_ATTR2 else ''
        vkey  = (size, color)
        if vkey not in seen:
            seen.add(vkey)
            stock_raw = row[C_STOCK].strip() if len(row) > C_STOCK else ''
            variants.append({
                'size':      size,
                'color':     color,
                'stock':     normalize_stock(stock_raw),
                'stock_raw': stock_raw,
            })
    name  = first[C_NAME].strip()
    sport = first[C_SPORT].strip()
    cat   = first[C_CAT].strip()
    products.append({
        'name':       name,
        'sport':      sport,
        'cat':        cat,
        'url':        first[C_URL].strip()  if len(first) > C_URL  else '',
        'sku':        first[C_SKU].strip()  if len(first) > C_SKU  else '',
        'price':      parse_price(first[C_PRICE] if len(first) > C_PRICE else ''),
        'sale':       parse_price(first[C_SALE]  if len(first) > C_SALE  else ''),
        'variants':   variants,
        'search_doc': build_search_doc(name, sport, cat,
                          first[C_SKU].strip() if len(first) > C_SKU else '', variants),
    })

output = {
    'updated':  datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'products': products,
}
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

in_stock = sum(1 for p in products if any(v['stock'] == 'in_stock' for v in p['variants']))
print(f'Wrote {len(products)} products ({in_stock} with stock) -> {OUT_FILE.stat().st_size // 1024} KB')
