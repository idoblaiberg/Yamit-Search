#!/usr/bin/env python3
"""
build_inventory.py — run after exporting CSVs from חישובית.
Reads the 4 CSV files and writes inventory.json to the repo.
Then: git add inventory.json && git push
The app fetches inventory.json on startup — no phone file upload needed.

Usage:
  python3 build_inventory.py
  python3 build_inventory.py --dir /path/to/csv/folder
"""

import csv, json, sys, os, re, glob
from datetime import datetime, timezone

# ── CONFIG ──
CSV_DIR  = os.path.dirname(os.path.abspath(__file__))  # same dir as script
OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.json')
COL_SKU  = 2
COL_NAME = 3
COL_ALT  = 4
COL_QTY  = 6

# Override CSV dir via --dir argument
if '--dir' in sys.argv:
    i = sys.argv.index('--dir')
    if i + 1 < len(sys.argv):
        CSV_DIR = sys.argv[i + 1]

def cat_from_filename(fn):
    f = fn.lower()
    if 'kite'  in f: return 'קייט'
    if 'wind'  in f: return 'גלישת רוח'
    if 'wing'  in f: return 'ווינג'
    if 'kayak' in f: return 'קיאק'
    return 'כללי'

def strip_stars(s):
    return s.strip().lstrip('*')

def split_csv_line(line):
    cols, cur, in_q = [], '', False
    for c in line:
        if c == '"':
            in_q = not in_q
        elif c == ',' and not in_q:
            cols.append(cur); cur = ''
        else:
            cur += c
    cols.append(cur)
    return cols

def parse_csv(path):
    items = []
    cat = cat_from_filename(os.path.basename(path))
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        text = f.read()
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        cols = split_csv_line(line)
        if len(cols) < 4:
            continue
        orig_name = (cols[COL_NAME] if len(cols) > COL_NAME else '').strip()
        sku  = strip_stars(cols[COL_SKU]  if len(cols) > COL_SKU  else '')
        name = strip_stars(orig_name)
        alt  = (cols[COL_ALT] if len(cols) > COL_ALT else '').strip()
        qty_str = (cols[COL_QTY] if len(cols) > COL_QTY else '').strip()

        if '***' in orig_name:
            label = orig_name.replace('*', '').strip()
            if len(label) > 1:
                cat = label
            continue

        if not name or len(name) < 2:
            continue
        if not sku or len(sku) < 3:
            continue

        try:
            qty = float(qty_str)
        except ValueError:
            qty = 0

        items.append({
            'n': name,
            's': sku,
            'a': alt,
            'c': cat,
            'q': qty,
            'i': 1 if qty > 0 else 0,
        })
    return items

def main():
    # Find all CSV files
    patterns = ['KITE*.csv', 'WINDSURF*.csv', 'WING*.csv', 'KAYAKS*.csv',
                'kite*.csv', 'windsurf*.csv', 'wing*.csv', 'kayaks*.csv']
    found = []
    for p in patterns:
        found.extend(glob.glob(os.path.join(CSV_DIR, p)))
    found = sorted(set(found))

    if not found:
        print(f'No CSV files found in {CSV_DIR}')
        print('Expected files matching: KITE*.csv, WINDSURF*.csv, WING*.csv, KAYAKS*.csv')
        sys.exit(1)

    all_items = []
    for path in found:
        items = parse_csv(path)
        in_stock = sum(1 for x in items if x['i'])
        print(f'  {os.path.basename(path)}: {len(items)} items ({in_stock} in stock)')
        all_items.extend(items)

    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    output = {
        'updated': now,
        'count': len(all_items),
        'items': all_items,
    }

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

    size_kb = os.path.getsize(OUT_FILE) / 1024
    in_stock_total = sum(1 for x in all_items if x['i'])
    print(f'\nWrote inventory.json: {len(all_items)} items ({in_stock_total} in stock), {size_kb:.0f} KB')
    print(f'Updated: {now}')
    print(f'\nNext step: git add inventory.json && git commit -m "update inventory" && git push')

if __name__ == '__main__':
    main()
