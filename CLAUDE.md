# Yamit Search V2 — Claude Context

## What this is
Single-file inventory search app for Yamit water sports store (Israel).
- **Deployed:** https://idoblaiberg.github.io/Yamit-Search
- **Target device:** iPhone Safari, in-store use
- **Stack:** single `index.html` + Fuse.js 7.x via CDN, no build step, no framework
- **Data:** `yamit_products.csv` (scraped daily from yamitysb.co.il) → `product_index.json` via `build_search.py`
- **AI:** Anthropic Claude Haiku with knowledge injection + `cache_control: ephemeral`

## Dev server
```bash
/opt/homebrew/bin/python3 -m http.server 8765 --directory /Users/ido/Documents/GitHub/Yamit-Search
```

## Critical constants in index.html
```js
CLAUDE_MODEL = 'claude-haiku-4-5-20251001'
FUSE_MAX = 40        // Fuse.js candidates passed to Claude
RES_MAX = 8          // Max Claude results
RES_MIN_SCORE = 0.4  // Min Claude score threshold
```

## Anthropic API — 3 required headers (missing any = silent fail)
```js
'x-api-key': key,
'anthropic-version': '2023-06-01',
'anthropic-dangerous-direct-browser-access': 'true'
```

## Search pipeline
1. **Fuse.js fuzzy** — searches `search_doc` field across 488 products, returns top 40
2. **Sport detection** — matches query keywords to `knowledge/*.txt` files
3. **Claude Haiku re-rank** — knowledge injected as `cache_control: ephemeral` block, returns top 8
4. **Fallback** — no API key → Fuse.js top 20 directly

## Data pipeline
```bash
# Run after yamit_products.csv is updated
/opt/homebrew/bin/python3 build_search.py
git add yamit_products.csv product_index.json && git commit -m "Daily update $(date +%Y-%m-%d)" && git push
```

## product_index.json structure
```json
{
  "updated": "2026-04-12T04:20:08Z",
  "products": [{
    "name": "FANATIC FLY 2024",
    "sport": "גלישת סאפ",
    "cat": "גלישת סאפ",
    "url": "https://yamitysb.co.il/product/fly-air-2022/",
    "sku": "...",
    "price": 6869,
    "sale": null,
    "variants": [
      { "size": "610", "color": "", "stock": "in_stock", "stock_raw": "נשארו במלאי רק 3" }
    ],
    "search_doc": "fanatic fly 2024 גלישת סאפ ..."
  }]
}
```

## Knowledge files (`knowledge/*.txt`)
Trimmed sport knowledge for Claude system prompt. ~100 tokens each.
Files: `master.txt`, `kite.txt`, `wing.txt`, `windsurf.txt`, `sup.txt`, `surf.txt`, `kayak.txt`, `clothing.txt`
Update manually when Claude skills are updated.

---

## index.html structure map (522 lines)

Read only the section you need — don't read the whole file.

| Lines | Section | What's there |
|-------|---------|--------------|
| 1–118 | `<head>` + `<style>` | CSS design tokens, card styles (`.card`, `.variants`, `.price-strike`, `.price-btn`, `.price-tag`) |
| 119 | Fuse.js CDN | `<script src="fuse.min.js">` |
| 120–142 | HTML: header + settings modal | `.hdr`, logo, badge (settings only — no upload button) |
| 144–167 | HTML: search screen | `#scrSearch` — search input, chips, `#nokeyBanner`, `#resultList` |
| 168–184 | JS: constants + `esc()` | `CLAUDE_MODEL`, `FUSE_MAX`, `RES_MAX`, `RES_MIN_SCORE`, data globals (`PRODUCTS`, `FUSE`, `KNOWLEDGE`) |
| 185–195 | JS: `esc()` | XSS escape helper |
| 197–232 | JS: settings + product index | `getKey/setKey`, `openSettings/closeSettings/saveSettings`, `loadProductIndex()`, `updateBadge()` |
| 234–299 | JS: sport detection + knowledge | `SPORT_ROUTES`, `detectSport()`, `buildKnowledgePrompt()`, `loadKnowledge()`, `fuzzySearch()` |
| 301–360 | JS: Claude client | `claudeSearch(query, candidates, apiKey, knowledgeText)` — knowledge injection + cache_control |
| 354–413 | JS: render | `buildCard(product)`, `buildSkeletons(n)`, `buildEmpty(icon, title, msg)` |
| 414–507 | JS: search logic | `fillSearch()`, key listener, `doSearch()` — Fuse → sport detect → Claude re-rank |
| 509–519 | JS: init | `showSearch()`, init IIFE — calls `loadProductIndex()` + `loadKnowledge()` |

### Key edit targets
- **Change Claude model** → line ~170 (`CLAUDE_MODEL`)
- **Change Fuse.js threshold** → inside `loadProductIndex()`, `threshold: 0.4`
- **Change max results** → lines ~172–174 (`FUSE_MAX`, `RES_MAX`, `RES_MIN_SCORE`)
- **Change card layout / price display** → `buildCard()` (~line 354)
- **Change Claude prompt** → instruction string inside `claudeSearch()` (~line 308)
- **Add a new search chip** → `.chips` div in HTML (~line 152)
- **Add sport to routing table** → `SPORT_ROUTES` array (~line 234)

---

## Known issues / decisions
- Write tool is blocked by security hook (innerHTML in code). Use Edit tool for targeted changes, or Bash heredoc for new files.
- Always use `/opt/homebrew/bin/python3`, never bare `python3`
- The store (yamitysb.co.il) blocks CORS for browser fetch — all data must be pre-built offline
- `build_search.py` groups rows by `(name, url)` — deduplicates variants by `(size, color)`
