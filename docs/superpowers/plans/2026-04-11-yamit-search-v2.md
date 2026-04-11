# Yamit Search V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace static multi-CSV inventory with daily-updated `yamit_products.csv` and upgrade search to Fuse.js fuzzy -> knowledge-injected Claude Haiku re-rank with grouped product cards.

**Architecture:** A Python build script (`build_search.py`) groups the daily CSV into `product_index.json` (~800 grouped products with pre-enriched `search_doc`). The app fetches this JSON at startup, builds a Fuse.js index in-memory, and runs a 3-stage search pipeline: fuzzy pre-filter -> sport detection -> Claude re-rank with cached knowledge context. Cards show one entry per product with color/size variants as plain text.

**Tech Stack:** Single-file `index.html` (no build step), Fuse.js 7.x via CDN, Claude Haiku API with `cache_control`, `/opt/homebrew/bin/python3`, `knowledge/*.txt` files fetched at startup.

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `knowledge/master.txt` | Cross-sport terminology for Claude system prompt |
| Create | `knowledge/kite.txt` | Kite brands, models, terms |
| Create | `knowledge/wing.txt` | Wing foil brands, models, terms |
| Create | `knowledge/windsurf.txt` | Windsurf brands, models, terms |
| Create | `knowledge/sup.txt` | SUP brands, models, terms |
| Create | `knowledge/surf.txt` | Surf brands, models, terms |
| Create | `knowledge/kayak.txt` | Kayak brands, models, terms |
| Create | `knowledge/clothing.txt` | Wetsuits/apparel brands, models, terms |
| Create | `build_search.py` | CSV -> grouped `product_index.json` with enriched `search_doc` |
| Create | `product_index.json` | Generated artifact committed to repo |
| Modify | `index.html` | All JS/HTML changes (tasks 4-9) |
| Delete | `build_inventory.py` | Replaced by build_search.py |
| Delete | `build_prices.py` | Prices now in CSV |
| Delete | `inventory.json` | Replaced by product_index.json |
| Delete | `prices.json` | Prices now in product_index.json |
| Delete | `sitemap_index.json` | URLs now in product_index.json |
| Modify | `CLAUDE.md` | Update structure map and retire old files |

---

## Task 1: Create knowledge files

**Files:** `knowledge/*.txt` (8 files)

Trimmed extracts from the Claude skills -- only what Claude needs to re-rank products. No narrative, no category trees. Write each file using your text editor or the method below.

- [ ] **Step 1: Create knowledge directory**

```bash
mkdir -p /Users/ido/Documents/GitHub/Yamit-Search/knowledge
```

- [ ] **Step 2: Write knowledge/master.txt**

Content:
```
Yamit water sports store (yamitysb.co.il). Exclusive Israeli importer of: Duotone, Fanatic, NELO, TIDERACE, BRACA PADDLES.
Always exclude secondhand items.
Construction tiers (Duotone/Fanatic): D/LAB=top carbon, SLS=premium, Concept Blue=sustainability, no-suffix=standard
Shared foil platform: AERO=mast/fuselage, CARVE wings (650-950cm2) compatible across Kite+Wing+Windsurf
Foil anatomy: toren=mast, guf/fuze=fuselage, knaf kadmit=front wing, stabilizer=rear wing, ALU=aluminum, karbon=carbon
Sport routing: sap/SUP=sup, surf/galim=surf, kait/kite=kite, wing=wing, ruah/windsurf=windsurf, kayak=kayak, halifa/wetsuit=clothing
Multi-sport: foil/poyel -> kite+wing+windsurf
Shared accessories: ION(all sports), wip(helmets/vests), StayCovered(car racks/bags)
Key Hebrew terms: glishn=board, mifras=sail, hupa=kite, kanaf=wing, poyel=hydrofoil, toren=mast, manor=boom, tarpez=harness, lish=leash, snapir=fin, nafah=volume, mitnapheh=inflatable, kashih=rigid
```

- [ ] **Step 3: Write knowledge/kite.txt**

Content:
```
Sport: kait surfing (Kitesurfing). Sole brand: Duotone. Exclusive importer.
Construction: D/LAB=top carbon, SLS=premium, Concept Blue=sustainability, no-suffix=standard
Kites (hupot): EVO(freeride) REBEL(big air) NEO(wave) VEGAS(freestyle) DICE JUICE(light wind/foil) MONO
Boards TT (twintip): JAIME SELECT SOLEIL(W) SPIKE TEAM-SERIES GONZALES BIG-AIR
Boards Wave: BLUR VOLT WHIP VOKE HYBRID PACE
Control bars: CLICK-BAR TRUST-BAR
Harnesses: ION APEX SOL RIOT AXXIS MUSE ECHO HADLOW B2 RIPPER
Foil: AERO=mast/fuselage, CARVE=front wings, shared platform with Wing+Windsurf
Brands: Duotone, ION, wip
Terms: hupa/kait=kite canopy, bar=control bar, tarpez=harness, toren=foil mast, tiuva/bladder=bladder, lish=leash
Sizes: kite 7-15m, twintip 130-145cm, foil wing 400-1400cm2
```

- [ ] **Step 4: Write knowledge/wing.txt**

Content:
```
Sport: wing foil. Brands: Duotone(wings+foils+boards), Fanatic(boards), ION(accessories). Exclusive importer.
Wings: UNIT(all-round) UNIT-SLS UNIT-D/LAB FLOAT-SLS STASH(parawing)
Wing sizes: 3.0-6.0m2
Boards: SKY-WING SKY-STYLE-SLS SKY-FREE SKY-START SKYBRID-SLS SKYBRID-D/LAB DOWNWINDER CRUSH-SLS STRIDER-SLS SKY-AIR
Board tiers: Original, SLS, D/LAB, TE(Team Edition)
Foil (AERO): AMP BLITZ WHIZZ FREE GLIDE CARVE CREST AERO-FREE, Fanatic-HA
Foil masts: AERO-Slim AERO-D/LAB AERO-SLS AERO-AL AERO-QM-ALU
Fabrics: Penta-TX(SLS), ALUULA(D/LAB), Concept-Blue(undyed)
Brands: Duotone, Fanatic, ION
Terms: wing/kanaf=wing canopy, lish-zeroa=wrist leash, lish-motnayim=waist leash, parvind=parawing
Sizes: wing 3-6m2, board 25-160L, foil wing 400-2000cm2
```

- [ ] **Step 5: Write knowledge/windsurf.txt**

Content:
```
Sport: glishat ruah (Windsurfing). Brands: Duotone(sails+boards), Fanatic(boards), ION(harnesses).
Boards(Fanatic): GECKO STINGRAY
Boards(Duotone): FALCON GRIP SKATE FREEWAVE EAGLE BLITZ BLAST STINGRAY RIPPER VIPER
Sails (mifrashot): SUPER-STAR SUPER-HERO SUPER-SESSION S_PACE E_PACE NOW DUKE HERO IDOL PACE WARP ALFA
Mast tiers: BLACK(50% carbon) SILVER(70%) GOLD(90%) PLATINUM(100%)
Mast types: SDM(standard diameter) RDM(reduced diameter)
Mast lengths: 370/400/430/460/490/520/550cm
Harnesses (ION): waist(motnayim), seat(yeshiva)
Brands: Duotone, Fanatic, ION, StayCovered
Terms: glishn-ruah=windsurf board, mifras=sail, toren=mast, manor=boom, tarpez=harness, SDM=standard mast, RDM=reduced mast, IMCS=stiffness index
Sizes: sail 2.5-8.8m2, mast 370-550cm, board 68-180L
```

- [ ] **Step 6: Write knowledge/sup.txt**

Content:
```
Sport: glishat sap (SUP). Exclusive importer of Fanatic.
Boards(Fanatic composite): ALLWAVE(wave/all-round) STUBBY(wave) PROWAVE(advanced) STYLEMASTER(longboard) FLY(all-round) FALCON(race) BLITZ(touring)
Boards(Fanatic inflatable): FLY-AIR
Paddles(QB/QuickBlade): ONO AVA STINGRAY T2 UV V-DRIVE KAHANA MICROFLY
Paddle tokens: CARBON HEX FLEX HYBRID FIXED ADJUSTABLE
Brands: Fanatic, QB/QuickBlade, ION(accessories+leashes)
Terms: sap=SUP board, kashih=rigid, mitnapheh=inflatable, mashhot=paddle, lish=leash, nafah=volume, mashhava=pump
Naming: FANATIC FLY 2024 10'6"x32" = model*year*length*width
Sizes: board 9-14ft, width 28-36in, volume 100-250L
```

- [ ] **Step 7: Write knowledge/surf.txt**

Content:
```
Sport: glishat galim (Wave Surfing).
Longboard brands: The Guild(Sequoia Bandito Poquito-Bandito Suit Kookling Noserider), Stewart(Redline Ripster Mighty-Flyer)
Shortboard brands: PIKO(Marilyn Mango, Israeli shaper), Rusty(Dwart-Too Hatchet Miso)
Softop brands: Future-Glide(FG), Focus
Semi-rigid: RYD
Fins: Koalition, RFC(Rainbow Fin Co), PIKO, QUOBA
Leashes+Accessories: StayCovered, ION
Terms: longboard(9ft+), shortboard, mid-length, fish, noserider, softop/foamie, semi-rigid, rocker, volume, fins, leash, wax
Sizes: board 5-10ft+, volume 20-80L
```

- [ ] **Step 8: Write knowledge/kayak.txt**

Content:
```
Sport: kayakim (Kayaks). Exclusive importer of NELO, TIDERACE, BRACA PADDLES.
Types: Olympic/sprint(K1/K2/K4), touring, surf-ski/OC(outrigger), whitewater, canoe polo, Sit-On-Top
NELO kayaks: SCORPIO(=surfski BOAT) CETUS DELPHIN VIRGO LEO BIW S60 B66
TIDERACE: touring sea kayaks
Whitewater: BURN MACHNO REACTR LOKI JED STOUT RIPPER
SOT: VELOCITY NEREUS CL370 CL470
Paddles(BRACA): SURFSKI TOURING OLYMPIC OUTRIGGER SUP -- PADDLES not boats
Other paddles: ROTOMOD WINNER BORA GENESIS ALUTEX ALPINA HURRICANE KINETIC
Brands: NELO, TIDERACE, BRACA, Yak(clothing), wip(helmets), ION
CRITICAL: kayak query -> prefer BOAT categories. SCORPIO=surfski BOAT. BRACA-SURFSKI=PADDLE only.
Terms: kayak, mashhot=paddle, hatirah=paddling, surfski, OC=outrigger, downwind, hatsait=spray deck, kasda=helmet, hege=rudder
```

- [ ] **Step 9: Write knowledge/clothing.txt**

Content:
```
Sport: bigud glisha (Wetsuits + Apparel). Shared across all sports.
Brands: O'Neill(main wetsuit), ION(wetsuits+vests+accessories), wip(helmets+vests)
O'Neill models: HYPERFREAK(premium) PSYCHO-TECH(warmest) EPIC(mid) REACTOR(entry)
O'Neill thickness: 3/2(spring/autumn), 4/3(winter), 5/4(cold winter)
O'Neill zip: FZ=front zip, BZ=back zip, NZ=no zip
ION wetsuits(men): SEEK-AMP SEEK-CORE ELEMENT STATIC
ION wetsuits(women): AMAZE-AMP AMAZE-CORE ELEMENT STATIC
Other categories: impact vest(afudat impact), buoyancy vest(afudat tsifah), helmet(kasda), gloves(kfafot), reef shoes/booties, surf hood(kova glisha)
Terms: halifa-glisha=wetsuit, neopren=neoprene, short-john=shorty, long-john, lycra/rashguard, poncho, FZ=front zip, BZ=back zip, NZ=no zip, thickness(ovhi)
Sizes: XS S M L XL XXL, gvarim=men, nashim=women, noar=youth
```

- [ ] **Step 10: Commit knowledge files**

```bash
cd /Users/ido/Documents/GitHub/Yamit-Search
git add knowledge/
git commit -m "Add trimmed knowledge files for Claude sport context"
```

---

## Task 2: Write build_search.py

**Files:** Create `build_search.py`

Column positions in yamit_products.csv (0-based, confirmed from header):
`ענף ספורט=0, קטגוריה=1, שם מוצר=2, תכונה 1=3, תכונה 2=4, מק"ט=5, מחיר רגיל=6, מחיר מבצע=7, מלאי=8, URL מוצר=9`

- [ ] **Step 1: Write the script**

Create `build_search.py` with your editor or via Bash. The script must:
1. Open `yamit_products.csv` with `encoding='utf-8-sig'` (handles BOM)
2. Use `csv.reader`, skip header row, use column indices (not column names) for reliability
3. Group rows by `(name, url)` tuple preserving insertion order
4. For each group: extract first row for product-level fields, iterate all rows for variants
5. Deduplicate variants by `(size, color)` pair
6. Normalize stock: `"in_stock"` if cell is non-empty and does not contain the Hebrew word for "sold out" (אזל = U+05D0 U+05D6 U+05DC); else `"out_of_stock"`
7. Build `search_doc` = lowercased name + sport + cat + sku + all sizes + all colors + brand synonyms for the sport
8. Write `{"updated": "<ISO timestamp>", "products": [...]}` to `product_index.json`

Full script (write this content to build_search.py):

```python
#!/usr/bin/env python3
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
    '\u05d2\u05dc\u05d9\u05e9\u05ea \u05e8\u05d5\u05d7': ['duotone', 'fanatic', 'ion'],
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
```

- [ ] **Step 2: Verify syntax**

```bash
/opt/homebrew/bin/python3 -m py_compile build_search.py && echo OK
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add build_search.py && git commit -m "Add build_search.py: CSV -> grouped product_index.json"
```

---

## Task 3: Generate and verify product_index.json

- [ ] **Step 1: Run build script**

```bash
cd /Users/ido/Documents/GitHub/Yamit-Search
/opt/homebrew/bin/python3 build_search.py
```

Expected: `Read ~1529 rows`, `Grouped into ~750-900 products`, `Wrote NNN products (NNN with stock) -> NNN KB`

- [ ] **Step 2: Spot-check JSON**

```bash
/opt/homebrew/bin/python3 -c "
import json
d = json.load(open('product_index.json'))
print('updated:', d['updated'], '| products:', len(d['products']))
p = d['products'][0]
print('first:', p['name'], '|', p['sport'], '|', len(p['variants']), 'variants')
print('search_doc:', p['search_doc'][:100])
m = next((p for p in d['products'] if any(v['color'] for v in p['variants'])), None)
if m: print('color variant:', m['name'], [(v['size'],v['color'],v['stock']) for v in m['variants'][:3]])
"
```

Verify: product count 700-900, `search_doc` has name + brand words, at least one product has color variants.

- [ ] **Step 3: Commit**

```bash
git add yamit_products.csv product_index.json
git commit -m "Generate product_index.json from yamit_products.csv"
```

---

## Task 4: index.html -- Add Fuse.js CDN + update constants + new globals

The Write tool is blocked for this file. Use Edit tool for all changes.

- [ ] **Step 1: Add Fuse.js CDN after closing style tag**

Find `</style>` (around line 108) and insert after it:
```html
<script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js"></script>
```

- [ ] **Step 2: Replace the CONSTANTS block**

Find `var CLAUDE_MODEL  = 'claude-haiku-4-5-20251001';` through `var RES_MIN_SCORE = 0.4;` and replace with:

```js
var CLAUDE_MODEL  = 'claude-haiku-4-5-20251001';
var CLAUDE_URL    = 'https://api.anthropic.com/v1/messages';
var STORAGE_KEY   = 'yamit_key';
var RES_MAX       = 8;
var RES_MIN_SCORE = 0.4;
var FUSE_MAX      = 40;

// ── DATA GLOBALS ──
var PRODUCTS         = [];   // loaded from product_index.json
var PRODUCTS_UPDATED = '';   // ISO timestamp
var KNOWLEDGE        = {};   // sport name -> text (loaded async)
var FUSE             = null; // Fuse.js instance (built after PRODUCTS loads)
```

- [ ] **Step 3: Commit**

```bash
git add index.html && git commit -m "index.html: add Fuse.js CDN, update constants, add data globals"
```

---

## Task 5: index.html -- Replace data layer

Remove old data code and add product_index loader + new updateBadge.

- [ ] **Step 1: Delete CSV parser block**

Delete everything from the `// ── CSV PARSER` comment through the closing brace of `splitCSVLine`.
Verify: `grep -n "parseCSV\|catFromFilename\|splitCSVLine" index.html` returns nothing.

- [ ] **Step 2: Delete PRICES + SITEMAP blocks**

Delete: `var PRICES`, `fetch('prices.json')` block, `PRICE_SKIP`, `findPrice()`, `var SITEMAP`, `fetch('sitemap_index.json')` block, `URL_SKIP`, `findProductUrl()`, `findSiblings()`.
Verify: `grep -n "PRICES\|SITEMAP\|findPrice\|findProductUrl\|findSiblings" index.html` returns nothing.

- [ ] **Step 3: Delete old inventory store**

Delete: `var INV = []`, `setInventory`, `saveToStorage`, `loadFromStorage`, old `updateBadge`.
Keep: `getKey`, `setKey`, `openSettings`, `closeSettings`, `saveSettings`, settings event listener.
Verify: `grep -n "var INV\|setInventory\|saveToStorage\|loadFromStorage" index.html` returns nothing.

- [ ] **Step 4: Insert product index loader + new updateBadge after settings block**

After the settings event listener (`document.getElementById('settingsOv').addEventListener...`), insert:

```js
// ── PRODUCT INDEX ──
function loadProductIndex() {
  return fetch('product_index.json')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (!data || !data.products || !data.products.length) return;
      PRODUCTS = data.products;
      PRODUCTS_UPDATED = data.updated || '';
      FUSE = new Fuse(PRODUCTS, {
        keys: ['search_doc'],
        threshold: 0.4,
        includeScore: true,
      });
      updateBadge();
    });
}

function updateBadge() {
  var total = PRODUCTS.length;
  var inStock = PRODUCTS.filter(function(p) {
    return p.variants.some(function(v) { return v.stock === 'in_stock'; });
  }).length;
  var el = document.getElementById('badge');
  if (total) {
    var age = '';
    if (PRODUCTS_UPDATED) {
      var days = Math.floor((Date.now() - new Date(PRODUCTS_UPDATED).getTime()) / 86400000);
      age = days === 0 ? ' \u00b7 \u05d4\u05d9\u05d5\u05dd' : ' \u00b7 ' + days + 'd';
    }
    el.textContent = inStock + '/' + total + age;
    el.className = 'badge on';
  } else {
    el.textContent = '\u05d8\u05d5\u05e2\u05df...';
    el.className = 'badge';
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add index.html && git commit -m "index.html: replace data layer with product_index fetch + new updateBadge"
```

---

## Task 6: index.html -- Replace preFilter with Fuse.js + sport detection + knowledge loader

- [ ] **Step 1: Delete the PREFILTER block**

Delete everything from `// ── PREFILTER` through the closing `}` of `preFilter()` (includes `TRANS`, `NUM_WORDS`, `preFilter`).
Verify: `grep -n "preFilter\|TRANS\|NUM_WORDS" index.html` returns nothing.

- [ ] **Step 2: Insert new block in place of old PREFILTER**

```js
// ── SPORT DETECTION + KNOWLEDGE ──
var SPORT_ROUTES = [
  { keys: ['\u05e1\u05d0\u05e4', 'sup', '\u05d2\u05dc\u05d9\u05e9\u05ea \u05e1\u05d0\u05e4'], file: 'sup' },
  { keys: ['\u05d2\u05dc\u05d9\u05e9\u05ea \u05d2\u05dc\u05d9\u05dd', 'surf', 'surfboard', '\u05dc\u05d5\u05e0\u05d2\u05d1\u05d5\u05e8\u05d3'], file: 'surf' },
  { keys: ['\u05e7\u05d9\u05d9\u05d8', 'kite', 'kitesurfing'], file: 'kite' },
  { keys: ['\u05d5\u05d5\u05d9\u05e0\u05d2', 'wing'], file: 'wing' },
  { keys: ['\u05d2\u05dc\u05d9\u05e9\u05ea \u05e8\u05d5\u05d7', 'windsurf', '\u05de\u05e4\u05e8\u05e9', '\u05d2\u05dc\u05e9\u05df \u05e8\u05d5\u05d7'], file: 'windsurf' },
  { keys: ['\u05e7\u05d9\u05d0\u05e7', 'kayak', '\u05e1\u05e8\u05e4\u05e1\u05e7\u05d9', 'surf ski', '\u05d7\u05ea\u05d9\u05e8\u05d4'], file: 'kayak' },
  { keys: ['\u05d7\u05dc\u05d9\u05e4\u05d4', 'wetsuit', '\u05d1\u05d9\u05d2\u05d5\u05d3', '\u05e0\u05d0\u05d5\u05e4\u05e8\u05df'], file: 'clothing' },
  { keys: ['\u05e4\u05d5\u05d9\u05dc', 'foil', 'hydrofoil'], files: ['kite', 'wing', 'windsurf'] },
];

function detectSport(query) {
  var q = query.toLowerCase();
  var files = {};
  SPORT_ROUTES.forEach(function(route) {
    if (route.keys.some(function(k) { return q.indexOf(k) !== -1; })) {
      var targets = route.file ? [route.file] : route.files;
      targets.forEach(function(f) { files[f] = true; });
    }
  });
  return Object.keys(files);
}

function buildKnowledgePrompt(sportFiles) {
  var parts = [];
  if (KNOWLEDGE['master']) parts.push(KNOWLEDGE['master']);
  sportFiles.forEach(function(f) { if (KNOWLEDGE[f]) parts.push(KNOWLEDGE[f]); });
  return parts.join('\n\n---\n\n');
}

function loadKnowledge() {
  ['master','kite','wing','windsurf','sup','surf','kayak','clothing'].forEach(function(name) {
    fetch('knowledge/' + name + '.txt')
      .then(function(r) { return r.text(); })
      .then(function(text) { KNOWLEDGE[name] = text; })
      .catch(function() {});
  });
}

// ── FUZZY SEARCH ──
function fuzzySearch(query) {
  if (!FUSE || !query.trim()) return [];
  return FUSE.search(query, { limit: FUSE_MAX }).map(function(r) { return r.item; });
}
```

- [ ] **Step 3: Commit**

```bash
git add index.html && git commit -m "index.html: add Fuse.js fuzzy search + sport detection + knowledge loader"
```

---

## Task 7: index.html -- Update claudeSearch (knowledge injection + cache_control)

- [ ] **Step 1: Replace claudeSearch function**

Find `async function claudeSearch(query, candidates, apiKey)` and replace the entire function with:

```js
// ── CLAUDE CLIENT ──
async function claudeSearch(query, candidates, apiKey, knowledgeText) {
  var list = candidates.map(function(p, i) {
    var inStock = p.variants.some(function(v) { return v.stock === 'in_stock'; });
    return i + '|' + (inStock ? '\u2713' : '\u2717') + '|' + esc(p.name) + '|' + esc(p.cat) + '|' + esc(p.sport);
  }).join('\n');

  var instruction = 'You are an inventory search assistant for an Israeli water sports store (Yamit).\n' +
    'Return ONLY a JSON array. Format: [{"idx":<n>,"score":<0.0-1.0>}]\n' +
    'Max ' + RES_MAX + ' results, min score ' + RES_MIN_SCORE + '. Prefer in-stock (\u2713).';

  var systemBlocks = [];
  if (knowledgeText) {
    systemBlocks.push({ type: 'text', text: knowledgeText, cache_control: { type: 'ephemeral' } });
  }
  systemBlocks.push({ type: 'text', text: instruction });

  var resp = await fetch(CLAUDE_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model: CLAUDE_MODEL,
      max_tokens: 400,
      system: systemBlocks,
      messages: [{ role: 'user', content: 'Query: "' + query + '"\n\nProducts:\n' + list }],
    }),
  });

  if (!resp.ok) {
    var err = await resp.json().catch(function() { return {}; });
    throw new Error(err.error && err.error.message ? err.error.message : 'HTTP ' + resp.status);
  }

  var data = await resp.json();
  var text = ((data.content && data.content[0] && data.content[0].text) || '[]')
    .replace(/```json|```/g, '').trim();
  var matches = JSON.parse(text);

  return matches
    .filter(function(m) { return typeof m.idx === 'number' && m.score >= RES_MIN_SCORE && candidates[m.idx]; })
    .sort(function(a, b) { return b.score - a.score; })
    .slice(0, RES_MAX)
    .map(function(m) { return candidates[m.idx]; });
}
```

- [ ] **Step 2: Commit**

```bash
git add index.html && git commit -m "index.html: Claude with knowledge injection and cache_control"
```

---

## Task 8: index.html -- Rewrite buildCard for grouped product variants

- [ ] **Step 1: Add .variants CSS**

In the style block, after `.tags { }`, add:
```css
.variants { font-size: 13px; color: #374151; margin: 4px 0 6px; line-height: 1.7; }
.price-strike { font-size: 13px; color: #9ca3af; text-decoration: line-through; margin-left: 4px; }
```

- [ ] **Step 2: Replace buildCard and delete buildGroupedResults**

Find `function buildCard(result)` and replace it (and delete the `buildGroupedResults` function that follows) with:

```js
// ── RENDER ──
function buildCard(product) {
  var inStock = product.variants.some(function(v) { return v.stock === 'in_stock'; });
  var cls  = inStock ? 'y' : 'n';
  var pill = inStock ? '\u05d1\u05de\u05dc\u05d0\u05d9' : '\u05d0\u05d6\u05dc';

  var hasSize  = product.variants.some(function(v) { return v.size; });
  var hasColor = product.variants.some(function(v) { return v.color; });
  var variantHtml = '';

  if (hasColor && hasSize) {
    // Group by color: "blue: S * M(check) / black: L(check) * XL"
    var colorMap = {}, colorOrder = [];
    product.variants.forEach(function(v) {
      var c = v.color || '\u2014';
      if (!colorMap[c]) { colorMap[c] = []; colorOrder.push(c); }
      colorMap[c].push(v);
    });
    variantHtml = colorOrder.map(function(c) {
      var sizes = colorMap[c].map(function(v) {
        return esc(v.size) + (v.stock === 'in_stock' ? '\u2713' : '');
      }).join(' \u00b7 ');
      return esc(c) + ': ' + sizes;
    }).join('<br>');
  } else if (hasColor) {
    variantHtml = product.variants.map(function(v) {
      return esc(v.color) + (v.stock === 'in_stock' ? '\u2713' : '');
    }).join(' \u00b7 ');
  } else if (hasSize) {
    variantHtml = product.variants.map(function(v) {
      return esc(v.size) + (v.stock === 'in_stock' ? '\u2713' : '');
    }).join(' \u00b7 ');
  }

  var priceHtml = '';
  if (product.sale) {
    priceHtml = '<span class="price-tag">\u20aa' + product.sale.toLocaleString('he-IL') + '</span>' +
                '<span class="price-strike">\u20aa' + (product.price || product.sale).toLocaleString('he-IL') + '</span>';
  } else if (product.price) {
    priceHtml = '<span class="price-tag">\u20aa' + product.price.toLocaleString('he-IL') + '</span>';
  }

  var btnHref  = product.url ||
    'https://yamitysb.co.il/?s=' + encodeURIComponent(product.name) + '&post_type=product';
  var btnLabel = product.url ? '\u05dc\u05d7\u05e0\u05d5\u05ea \u2197' : '\u05d7\u05d9\u05e4\u05d5\u05e9 \u2197';

  return '<div class="card ' + cls + '">' +
    '<div class="ctop">' +
      '<div class="cname">' + esc(product.name) + '</div>' +
      '<div class="pill ' + cls + '">' + pill + '</div>' +
    '</div>' +
    '<div class="tags">' +
      '<span class="tag">' + esc(product.cat) + '</span>' +
      (product.sku ? '<span class="tag">' + esc(product.sku) + '</span>' : '') +
    '</div>' +
    (variantHtml ? '<div class="variants">' + variantHtml + '</div>' : '') +
    '<div class="cfoot">' +
      '<div class="reason"></div>' +
      priceHtml +
      '<a class="price-btn" href="' + esc(btnHref) + '" target="_blank" rel="noopener">' + btnLabel + '</a>' +
    '</div>' +
    '</div>';
}
```

- [ ] **Step 3: Commit**

```bash
git add index.html && git commit -m "index.html: rewrite buildCard for grouped product variants"
```

---

## Task 9: index.html -- Update doSearch + remove upload screen + update init

- [ ] **Step 1: Replace doSearch**

Find `async function doSearch()` and replace the entire function with:

```js
async function doSearch() {
  var query     = document.getElementById('searchInput').value.trim();
  if (!query) return;

  var apiKey    = getKey();
  var rl        = document.getElementById('resultList');
  var stl       = document.getElementById('statusLine');
  var nokeyEl   = document.getElementById('nokeyBanner');
  var searchBtn = document.getElementById('searchBtn');

  if (!PRODUCTS.length) {
    rl.innerHTML = buildEmpty('\ud83d\udce6', '\u05d8\u05d5\u05e2\u05df \u05de\u05dc\u05d0\u05d9...', '\u05d0\u05e0\u05d0 \u05d4\u05de\u05ea\u05df');
    return;
  }

  searchBtn.disabled = true;
  nokeyEl.classList.remove('show');
  stl.textContent = '\u05de\u05e1\u05e0\u05df \u05de\u05d5\u05e2\u05de\u05d3\u05d9\u05dd...';
  rl.innerHTML = buildSkeletons(4);

  try {
    // Stage 1: Fuse.js fuzzy
    var candidates = fuzzySearch(query);

    if (!candidates.length) {
      rl.innerHTML = buildEmpty('\ud83e\udd14', '\u05dc\u05d0 \u05e0\u05de\u05e6\u05d0', '\u05e0\u05e1\u05d4 \u05de\u05d5\u05e0\u05d7 \u05d0\u05d7\u05e8 \u2014 EVO 10, \u05e8\u05d9\u05d1\u05dc 9, kayak');
      stl.textContent = '';
      searchBtn.disabled = false;
      return;
    }

    var products;

    if (!apiKey) {
      // Fallback: show Fuse.js top 20 directly
      nokeyEl.classList.add('show');
      products = candidates.slice(0, 20);
      stl.textContent = products.length + ' \u05ea\u05d5\u05e6\u05d0\u05d5\u05ea (\u05de\u05d9\u05dc\u05d5\u05ea \u05de\u05e4\u05ea\u05d7)';
    } else {
      // Stage 2+3: detect sport -> build knowledge -> Claude re-rank
      var sportFiles    = detectSport(query);
      var knowledgeText = buildKnowledgePrompt(sportFiles);
      stl.textContent   = candidates.length + ' \u05de\u05d5\u05e2\u05de\u05d3\u05d9\u05dd \u2192 Claude...';
      products = await claudeSearch(query, candidates, apiKey, knowledgeText);
      stl.textContent   = products.length ? products.length + ' \u05ea\u05d5\u05e6\u05d0\u05d5\u05ea' : '';
    }

    if (!products.length) {
      rl.innerHTML = buildEmpty('\ud83e\udd37', '\u05d0\u05d9\u05df \u05ea\u05d5\u05e6\u05d0\u05d5\u05ea', '\u05e0\u05e1\u05d4: EVO 10, \u05e8\u05d9\u05d1\u05dc 9, \u05e7\u05d9\u05d0\u05e7, wing foil');
    } else {
      rl.innerHTML = '<div class="rlist">' + products.map(buildCard).join('') + '</div>';
    }
  } catch(e) {
    rl.innerHTML = buildEmpty('\u26a0\ufe0f', '\u05e9\u05d2\u05d9\u05d0\u05d4', esc(e.message));
    stl.textContent = '';
  }

  searchBtn.disabled = false;
}
```

- [ ] **Step 2: Remove upload screen HTML**

Delete the entire `<div id="scrUpload"...>...</div>` block from the HTML.

- [ ] **Step 3: Remove upload JavaScript**

Delete: `pendingFiles` var, fileInput change listener, drag-drop listeners, `showPendingFiles`, `doLoad`, `readFileAsText`, `showUpload`, `renderCurrentInvStatus`.

- [ ] **Step 4: Replace the init IIFE**

Find `(function init() {` and replace the entire block with:

```js
// ── NAVIGATION + INIT ──
function showSearch() {
  document.getElementById('scrSearch').classList.add('show');
  document.getElementById('searchInput').focus();
}

(function init() {
  showSearch();
  loadProductIndex().catch(function() {});
  loadKnowledge();
})();
```

- [ ] **Step 5: Commit**

```bash
git add index.html && git commit -m "index.html: replace doSearch pipeline, remove upload screen, update init"
```

---

## Task 10: Smoke test

- [ ] **Step 1: Start dev server**

```bash
/opt/homebrew/bin/python3 -m http.server 8765 --directory /Users/ido/Documents/GitHub/Yamit-Search &
```

- [ ] **Step 2: Open http://localhost:8765 in Safari and check each item**

- [ ] No JS console errors on load
- [ ] Badge shows `NNN/NNN * היום` within 2s
- [ ] Search "evo 10": kite canopy results, sizes shown (e.g. `7 * 9 * 10(check) * 12(check)`)
- [ ] Search "reactor": clothing results with color groups (`blue: S * M(check) / black: L(check) * XL`)
- [ ] No API key: Fuse.js top 20 shown, nokeyBanner visible
- [ ] With API key: status shows "N candidates -> Claude..."
- [ ] Card price shown inline (e.g. NIS 8500)
- [ ] Button says "to store" and links to direct product URL
- [ ] No upload screen visible
- [ ] No 404 errors for inventory.json / prices.json / sitemap_index.json

- [ ] **Step 3: Kill dev server**

```bash
kill %1
```

---

## Task 11: Cleanup + push

- [ ] **Step 1: Delete retired files**

```bash
cd /Users/ido/Documents/GitHub/Yamit-Search
rm -f build_inventory.py build_prices.py inventory.json prices.json sitemap_index.json
```

- [ ] **Step 2: Update CLAUDE.md**

- Remove COL_SKU / COL_NAME / COL_QTY from "Critical constants" section
- Update "Active feature" to describe V2 architecture (product_index.json + knowledge/ + Fuse.js)
- Update "index.html structure map" line ranges (run `grep -n "CONSTANTS\|PRODUCT INDEX\|SETTINGS\|SPORT DETECTION\|CLAUDE CLIENT\|RENDER\|SEARCH SCREEN\|NAVIGATION" index.html`)
- Add `product_index.json` and `knowledge/` to the data section
- Mark all V2 items complete in progress tracker

- [ ] **Step 3: Final commit and push**

```bash
cd /Users/ido/Documents/GitHub/Yamit-Search
git add -A
git commit -m "Yamit Search V2: daily CSV + Fuse.js fuzzy + knowledge-injected Claude re-rank"
git push
```

Verify https://idoblaiberg.github.io/Yamit-Search after ~60 seconds.

---

## Daily scraper command (add as final step in your existing task)

```bash
/opt/homebrew/bin/python3 build_search.py && git add yamit_products.csv product_index.json && git commit -m "Daily update $(date +%Y-%m-%d)" && git push
```
