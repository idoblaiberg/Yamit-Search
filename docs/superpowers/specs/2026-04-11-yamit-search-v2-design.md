# Yamit Search V2 — Design Spec
**Date:** 2026-04-11

## Overview

Replace the static multi-CSV inventory system with a daily-updated single CSV from Google Drive, and upgrade the search pipeline from keyword+Claude to a three-layer Fuse.js fuzzy → knowledge-injected Claude Haiku re-rank system.

---

## 1. Data Architecture

### Source

`yamit_products.csv` — scraped daily from yamitysb.co.il, uploaded to Google Drive (file ID: `19DvaQHvMKmCz8rN6Wt3jqK5jnPNrKmbT`, public "anyone with link").

The daily scraper task gains one extra step:
```bash
cd /Users/ido/Documents/GitHub/Yamit-Search && git add yamit_products.csv product_index.json && git commit -m "Daily update $(date +%Y-%m-%d)" && git push
```

### CSV columns

| Column | Content |
|---|---|
| ענף ספורט | Sport category (Hebrew) |
| קטגוריה | Sub-category (Hebrew) |
| שם מוצר | Product name (Hebrew + English mixed) |
| תכונה 1 | Variant attribute 1 (size, volume, length…) |
| תכונה 2 | Variant attribute 2 (color) |
| מק"ט | SKU |
| מחיר רגיל (₪) | Regular price |
| מחיר מבצע (₪) | Sale price (may be empty) |
| מלאי | Stock status (Hebrew: "קיים במלאי" / "אזל" / "נשארו במלאי רק N") |
| URL מוצר | Direct product URL |

### Build script: `build_search.py`

Replaces `build_inventory.py`, `build_prices.py`. Single script, one output.

**Input:** `yamit_products.csv`
**Output:** `product_index.json`

**Algorithm:**
1. Parse CSV (UTF-8-BOM, skip rows with empty product name)
2. Group rows by `(שם מוצר, URL מוצר)` — each group = one product
3. For each group, build a product object:
   - `name` — product name
   - `sport` — sport category
   - `cat` — sub-category
   - `url` — product URL (from first row in group)
   - `price` — regular price as integer (from first row; null if empty)
   - `sale` — sale price as integer (null if empty)
   - `variants` — list of `{ size, color, stock }` objects (one per CSV row)
     - `size` = תכונה 1 (stripped, empty string if blank)
     - `color` = תכונה 2 (stripped, empty string if blank)
     - `stock` = normalized stock string (see below)
   - `search_doc` — enriched text blob for Fuse.js (see below)
4. Write JSON array to `product_index.json`

**Stock normalization:**
- "קיים במלאי" → `"in_stock"`
- "נשארו במלאי רק N" → `"in_stock"` (N is visible in variant display)
- "אזל" or empty → `"out_of_stock"`

Keep raw stock string too (`stock_raw`) for display purposes.

**`search_doc` enrichment:**
Concatenate (space-separated, lowercase):
- Product name
- Sport and category
- SKU
- All unique size values from variants
- All unique color values from variants
- Brand synonyms: look up sport in `knowledge/{sport}.txt`, extract brand name aliases (e.g. "fanatic פנטיק", "duotone דואוטון")

This is the text Fuse.js indexes. It enables matching "פנטיק" to a product named "FANATIC", or "610" to a specific size variant.

### `product_index.json` structure

```json
[
  {
    "name": "FANATIC FLY 2024",
    "sport": "גלישת סאפ",
    "cat": "גלישת סאפ",
    "url": "https://yamitysb.co.il/product/fly-air-2022/",
    "price": 6869,
    "sale": 6250,
    "variants": [
      { "size": "610", "color": "", "stock": "in_stock", "stock_raw": "נשארו במלאי רק 3" },
      { "size": "69",  "color": "", "stock": "out_of_stock", "stock_raw": "אזל" }
    ],
    "search_doc": "fanatic fly 2024 גלישת סאפ sup board fanatic פנטיק fly 610 69"
  }
]
```

### What gets retired

| Removed | Replaced by |
|---|---|
| `inventory.json` + `build_inventory.py` | `product_index.json` + `build_search.py` |
| `prices.json` + `build_prices.py` | `price` / `sale` fields in `product_index.json` |
| `sitemap_index.json` | `url` field in `product_index.json` |
| CSV upload screen + drag-drop UI | Auto-fetch at startup |
| 4 static CSVs (KITE, WINDSURF, WING, KAYAKS) | `yamit_products.csv` |
| `findPrice()`, `findProductUrl()` JS functions | Direct field access |

---

## 2. Knowledge Files

### Source

Extracted and trimmed from the 8 Claude Code personal skills:
`yamit-master-knowledge`, `yamit-kite-knowledge`, `yamit-windsurf-knowledge`,
`yamit-wing-knowledge`, `yamit-sup-knowledge`, `yamit-surf-knowledge`,
`yamit-kayak-knowledge`, `yamit-clothing-knowledge`

### Output

`knowledge/master.txt` + `knowledge/{sport}.txt` for each of 7 sports.
Committed to repo. Updated manually only when the Claude skills are updated.

### Trimming rule

Keep only what Claude needs to re-rank products:
- Terminology table (Hebrew ↔ English)
- Brand/model token list
- Construction tier tokens (D/LAB, SLS, etc.)

Drop: category trees, detailed accessory lists, narrative explanations, spare-part details.

**Target size:** ~400–600 tokens per file. Master + one sport file combined: ~1,000 tokens.

### Example trimmed `knowledge/kite.txt`

```
Sport: קייט סרפינג (Kitesurfing). Sole brand: Duotone. Exclusive Israeli importer.
Construction: D/LAB=top carbon · SLS=premium · Concept Blue=sustainability · no-suffix=standard
Kites: EVO(freeride) REBEL(big air) NEO(wave) VEGAS(freestyle) DICE JUICE(light wind) MONO
Boards-TT: JAIME SELECT SOLEIL(W) SPIKE TEAM-SERIES
Boards-Wave: BLUR VOLT WHIP VOKE HYBRID PACE
Harnesses: ION APEX SOL RIOT AXXIS MUSE ECHO HADLOW
Foil: AERO=mast/fuselage · CARVE=wings · shared platform with Wing+Windsurf
Terms: חופה=kite · בר=control bar · טרפז=harness · תורן=foil mast · גוף/פיוז=fuselage · טיובה=bladder · ליש=leash
```

### Sport routing table (baked into JS)

Mirrors the master skill routing. Maps query keywords → knowledge file(s) to load:

| Keywords | File(s) |
|---|---|
| סאפ · SUP · stand up paddle | `sup` |
| גלישת גלים · surf · surfboard | `surf` |
| קייט · kite · kitesurfing | `kite` |
| ווינג · wing · wing foil | `wing` |
| גלישת רוח · windsurf · windsurfing | `windsurf` |
| קיאק · kayak · סרפסקי · surf ski | `kayak` |
| חליפה · wetsuit · ביגוד · נאופרן | `clothing` |
| פויל (ambiguous) | `kite` + `wing` + `windsurf` |

Multi-sport queries load multiple files; combined token count stays under 1,500.

---

## 3. Search Pipeline

### Startup

1. Fetch `product_index.json` → build Fuse.js index on `search_doc` field
2. Fetch all `knowledge/*.txt` files → store in memory keyed by sport name
3. Show age badge ("היום" / "Nd") based on last git commit date embedded in JSON

### On every query

**Stage 1 — Fuse.js fuzzy (always runs)**
- Search `search_doc` across all ~800 products
- Returns top 40 candidates with fuzzy score
- Handles: typos, partial SKUs, mixed Hebrew/English, size numbers, brand aliases

**Stage 2 — Sport detection**
- Scan query against routing table keywords
- Select knowledge file(s)
- Falls back to `master.txt` alone if no sport detected

**Stage 3 — Claude Haiku re-rank (when API key present)**
- System prompt = `master.txt` + relevant sport file(s), marked `cache_control: ephemeral`
- User message = query + top 40 candidates (name, sport, price, stock summary)
- Claude returns ranked list of top 10 product names
- Map names back to full product objects for rendering

**Fallback chain:**
- No API key → render Fuse.js top 20 directly
- Claude error / timeout → render Fuse.js top 20 with silent fallback (no error shown)

### Prompt caching

System prompt uses `cache_control: ephemeral`. After the first search in a session, the knowledge portion is served from cache at $0.025/M tokens (vs $0.25/M input) — 10× cheaper. Cost per search after first: effectively the same as today.

---

## 4. UI: Grouped Product Cards

### Card layout

```
┌─────────────────────────────────────────────────┐
│ DUOTONE EVO SLS 2025                            │
│ קייט סרפינג · חופות · SKU123                   │
│                                                 │
│ 7 · 9 · 12✓ · 14✓                              │  ← sizes only
│                                                 │
│ ₪8,500                          ↗ yamitysb      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ ION REACTOR WETSUIT                             │
│ ביגוד גלישה · חליפות · SKU456                  │
│                                                 │
│ כחול: S · M✓                                   │  ← color groups when
│ שחור: L✓ · XL                                  │     both attrs present
│                                                 │
│ ₪400                            ↗ yamitysb      │
└─────────────────────────────────────────────────┘
```

### Variant display logic

| Variant type | Display |
|---|---|
| Sizes only (attr2 empty) | Single line: `S · M✓ · L✓ · XL` |
| Colors only (attr1 empty) | Single line: `כחול✓ · שחור` |
| Both size + color | One line per color: `כחול: S · M✓` / `שחור: L✓ · XL` |
| No variants (single SKU) | No variant line shown |

`✓` suffix = `stock === "in_stock"`. No mark = אזל. Plain text, no bubbles/chips.

### Price display

- Sale price available: show sale in red, regular struck through
- Regular price only: show regular price
- No price: show nothing (no "contact for price" text)

### Link

"↗ yamitysb" button links directly to `url` field. No fallback to site search needed (URL always present in CSV).

### Removed UI elements

- CSV upload screen and drag-drop zone
- File list + "load" button
- Settings: HF token field (no longer needed)

---

## 5. Implementation Files

| File | Action |
|---|---|
| `index.html` | Major rewrite — remove upload screen, replace CSV parser + inventory store with product_index fetch, replace preFilter with Fuse.js, update Claude call to inject knowledge + cache_control, rewrite buildCard for grouped variants |
| `build_search.py` | New — replaces build_inventory.py + build_prices.py |
| `knowledge/master.txt` | New — trimmed from yamit-master-knowledge skill |
| `knowledge/kite.txt` | New — trimmed from yamit-kite-knowledge skill |
| `knowledge/windsurf.txt` | New — trimmed from yamit-windsurf-knowledge skill |
| `knowledge/wing.txt` | New — trimmed from yamit-wing-knowledge skill |
| `knowledge/sup.txt` | New — trimmed from yamit-sup-knowledge skill |
| `knowledge/surf.txt` | New — trimmed from yamit-surf-knowledge skill |
| `knowledge/kayak.txt` | New — trimmed from yamit-kayak-knowledge skill |
| `knowledge/clothing.txt` | New — trimmed from yamit-clothing-knowledge skill |
| `product_index.json` | Generated artifact — committed to repo |
| `build_inventory.py` | Delete |
| `build_prices.py` | Delete |
| `inventory.json` | Delete |
| `prices.json` | Delete |
| `sitemap_index.json` | Delete |

---

## 6. Fuse.js Integration

Loaded from CDN (no build step): `https://cdn.jsdelivr.net/npm/fuse.js/dist/fuse.min.js`

Config:
```js
new Fuse(products, {
  keys: ['search_doc'],
  threshold: 0.4,      // higher = more fuzzy
  includeScore: true,
  useExtendedSearch: false
})
```

Threshold 0.4 is a starting point — tune after testing with real queries.
