# ימית — חיפוש מלאי

Natural language inventory search for Yamit water sports store, built for in-store use on iPhone Safari.

**Live app:** https://idoblaiberg.github.io/Yamit-Search

---

## What it does

Staff type a query in Hebrew or English — `EVO 10`, `ריבל 9`, `wing foil` — and get ranked results from the full inventory with stock status and store price. Claude AI handles the ranking; a keyword fallback works without an API key.

---

## Quick start (first time)

1. Open https://idoblaiberg.github.io/Yamit-Search on your phone
2. Inventory loads automatically from `inventory.json`
3. Tap **⚙** → enter your Claude API key → Save
4. Search

> No API key? The app still works with keyword-only results.

**Add to home screen:** Safari → Share → Add to Home Screen for a fullscreen app icon.

---

## Updating inventory

Inventory is stored in `inventory.json` in this repo. The app fetches it on every startup and updates silently if a newer version is available.

**When to update:** after exporting fresh CSVs from חישובית.

```bash
# 1. Place the 4 CSV exports in this folder
#    KITE_*.csv  WINDSURF_*.csv  WING_*.csv  KAYAKS_*.csv

# 2. Build inventory.json
python3 build_inventory.py

# 3. Push — phone gets the update on next app open
git add inventory.json
git commit -m "update inventory $(date +%Y-%m-%d)"
git push
```

The badge on the app shows `1008/2564 · היום` — in-stock / total · age of data.

---

## Updating prices

Prices are stored in `prices.json` — a catalogue of all products on yamitysb.co.il with their price range and exact URL. Run this when prices change (seasonally, or after new product launch).

```bash
# Takes ~5–8 minutes — scrapes ~2,690 product pages
python3 build_prices.py

git add prices.json
git commit -m "update prices $(date +%Y-%m-%d)"
git push
```

Each search result card shows the price inline (e.g. `₪7,600–₪9,650`) and the **מחיר ↗** button links directly to the exact product page on the store.

---

## Files

| File | Purpose |
|------|---------|
| `index.html` | The entire app — HTML, CSS, JS in one file |
| `inventory.json` | Pre-built inventory (2,564 items). Fetched by app on startup |
| `prices.json` | Price catalogue scraped from yamitysb.co.il (~2,690 entries) |
| `build_inventory.py` | Converts CSV exports → `inventory.json` |
| `build_prices.py` | Scrapes yamitysb.co.il → `prices.json` |
| `CLAUDE.md` | Developer context for Claude Code sessions |

---

## How search works

```
Query
  │
  ▼
PreFilter — keyword match + Hebrew↔English transliteration
  │         scores up to 80 candidates
  ▼
Claude Haiku — ranks candidates, returns up to 8 results with Hebrew reason
  │
  ▼
Result cards — name, stock qty, category, SKU, price range, store link
```

**Transliteration examples:** `EVO` ↔ `איבו`, `REBEL` ↔ `ריבל`, `NEO` ↔ `נאו`

**No API key:** skips Claude, returns top 20 keyword matches directly.

---

## Requirements

- Python 3.8+ (for build scripts) — use `/opt/homebrew/bin/python3` on Mac
- Claude API key from [platform.anthropic.com](https://platform.anthropic.com) (optional but recommended)
- Internet access to push updates; app works offline after first load

---

## Dev server

```bash
/opt/homebrew/bin/python3 -m http.server 8765 --directory /path/to/Yamit-Search
# Open http://localhost:8765
```

> Must serve over HTTP (not `file://`) for `fetch()` calls to work.

---

## Contributing / making changes

The entire app is in `index.html` — no build step, no dependencies to install. Edit the file and refresh the browser.

**Before making changes**, read `CLAUDE.md` — it has a line-by-line structure map of `index.html` so you can jump directly to the right section without reading the whole file. Key targets:

| Change | Where |
|--------|-------|
| Add a Hebrew↔English word pair | `index.html` line ~353 (`TRANS` object) |
| Change Claude model | `index.html` line ~179 |
| Adjust max results | `index.html` lines ~187–189 (`PRE_MAX`, `RES_MAX`) |
| Card layout / price display | `index.html` lines ~467–512 (`buildCard`) |
| Claude system prompt | `index.html` lines ~420–428 |
| Add a search chip shortcut | `index.html` lines ~157–164 |

**Deploying:** push `main` → GitHub Pages rebuilds automatically (1–2 min).
