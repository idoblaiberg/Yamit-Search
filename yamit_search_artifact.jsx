import { useState, useMemo, useRef, useCallback, useEffect } from "react";
import Papa from "papaparse";

const CLAUDE_MODEL = "claude-haiku-4-5-20251001";
const CLAUDE_URL = "https://api.anthropic.com/v1/messages";

const SPORT_COLORS = {
  "גלישת סאפ": "#3b82f6",
  "קייט סרפינג": "#f59e0b",
  "גלישת רוח": "#10b981",
  "ווינג פויל": "#8b5cf6",
  "גלישת גלים": "#ef4444",
  "ביגוד גלישה": "#ec4899",
  "קיאקים": "#06b6d4",
};

const COL = {
  sport:    ["ענף ספורט", "ענף"],
  category: ["קטגוריה"],
  name:     ["שם מוצר", "שם"],
  sku:      ['מק"ט', "מקט", "sku"],
  regular:  ["מחיר רגיל (₪)", "מחיר רגיל", "regular_price"],
  sale:     ["מחיר מבצע (₪)", "מחיר מבצע", "sale_price"],
  stock:    ["מלאי", "stock"],
  url:      ["URL מוצר", "url", "URL"],
};

function resolveCol(headers, aliases) {
  for (const a of aliases) {
    const h = headers.find(h => h.trim() === a);
    if (h) return h;
  }
  return null;
}

function parseCSV(file) {
  return new Promise((res, rej) => {
    Papa.parse(file, {
      header: true, skipEmptyLines: true, encoding: "UTF-8",
      complete: r => {
        const headers = r.meta.fields || [];
        const cols = Object.fromEntries(
          Object.entries(COL).map(([k, aliases]) => [k, resolveCol(headers, aliases)])
        );
        const products = r.data.map(row => ({
          sport:    row[cols.sport]    || "",
          category: row[cols.category] || "",
          name:     row[cols.name]     || "",
          sku:      row[cols.sku]      || "",
          regular:  row[cols.regular]  || "",
          sale:     row[cols.sale]     || "",
          stock:    row[cols.stock]    || "",
          url:      row[cols.url]      || "",
        })).filter(p => p.name);
        res(products);
      },
      error: rej,
    });
  });
}

function priceNum(s) {
  return parseFloat(String(s).replace(/[^\d.]/g, "")) || 0;
}

async function smartSearch(query, categoryIndex, apiKey) {
  const res = await fetch(CLAUDE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model: CLAUDE_MODEL,
      max_tokens: 300,
      system: `אתה עוזר לחפש מוצרי גלישה.
החזר JSON בלבד (ללא markdown) עם המפתחות:
{ "sports": [], "categories": [], "keywords": [], "brand": null, "size": null }
השתמש רק בקטגוריות מהרשימה הבאה — אל תמציא:
${JSON.stringify(categoryIndex)}`,
      messages: [{ role: "user", content: query }],
    }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  const data = await res.json();
  return JSON.parse(data.content[0].text);
}

function ProductCard({ p }) {
  const hasSale = !!p.sale;
  const color   = SPORT_COLORS[p.sport] || "#6b7280";
  const inStock = p.stock && !p.stock.includes("אזל");
  return (
    <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e5e7eb",
      padding: "12px 14px", position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: 0, right: 0, width: 4, height: "100%",
        background: color, borderRadius: "0 12px 12px 0" }} />
      <div style={{ marginLeft: 4 }}>
        <div style={{ fontWeight: 600, fontSize: 15, lineHeight: 1.35, marginBottom: 4 }}>
          {p.url
            ? <a href={p.url} target="_blank" rel="noreferrer"
                style={{ color: "#111", textDecoration: "none" }}>{p.name}</a>
            : p.name}
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 6,
          fontSize: 12, color: "#6b7280" }}>
          <span style={{ background: "#f3f4f6", borderRadius: 4, padding: "1px 6px" }}>{p.sport}</span>
          {p.category && <span style={{ background: "#f3f4f6", borderRadius: 4,
            padding: "1px 6px" }}>{p.category}</span>}
          {p.sku && <span style={{ fontFamily: "monospace", color: "#9ca3af" }}>{p.sku}</span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            {hasSale ? <>
              <span style={{ fontWeight: 700, fontSize: 17, color: "#ef4444" }}>₪{p.sale}</span>
              <span style={{ fontSize: 13, color: "#9ca3af", textDecoration: "line-through" }}>₪{p.regular}</span>
            </> : p.regular
              ? <span style={{ fontWeight: 700, fontSize: 17 }}>₪{p.regular}</span>
              : null}
          </div>
          <span style={{ fontSize: 12, fontWeight: 600,
            color: inStock ? "#16a34a" : "#ef4444" }}>{p.stock}</span>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [products,     setProducts]     = useState([]);
  const [loading,      setLoading]      = useState(false);
  const [search,       setSearch]       = useState("");
  const [sport,        setSport]        = useState("");
  const [onSale,       setOnSale]       = useState(false);
  const [inStock,      setInStock]      = useState(false);
  const [sort,         setSort]         = useState("default");
  const [dragging,     setDragging]     = useState(false);

  // Smart search state
  const [aiFilter,     setAiFilter]     = useState(null);   // Claude JSON response
  const [aiLoading,    setAiLoading]    = useState(false);
  const [aiBadge,      setAiBadge]      = useState(null);   // "קייט סרפינג > ריבלים"
  const [apiKey,       setApiKey]       = useState(() => localStorage.getItem("yamit_apiKey") || "");
  const [showSettings, setShowSettings] = useState(false);
  const [apiKeyDraft,  setApiKeyDraft]  = useState("");

  const fileRef    = useRef();
  const debounceRef = useRef(null);

  // Build category index from loaded products
  const categoryIndex = useMemo(
    () => [...new Set(products.map(p => `${p.sport} > ${p.category}`).filter(Boolean))],
    [products]
  );

  async function loadFile(file) {
    if (!file) return;
    setLoading(true);
    try {
      const prods = await parseCSV(file);
      setProducts(prods);
      setAiFilter(null);
      setAiBadge(null);
    } catch (e) { alert("שגיאה: " + e.message); }
    setLoading(false);
  }

  function openSettings() {
    setApiKeyDraft(apiKey);
    setShowSettings(true);
  }

  function saveSettings() {
    localStorage.setItem("yamit_apiKey", apiKeyDraft);
    setApiKey(apiKeyDraft);
    setShowSettings(false);
  }

  // Debounced smart search on input change
  const handleSearchChange = useCallback((e) => {
    const q = e.target.value;
    setSearch(q);
    setAiFilter(null);
    setAiBadge(null);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q.trim() || !apiKey) return;

    debounceRef.current = setTimeout(async () => {
      setAiLoading(true);
      try {
        const json = await smartSearch(q, categoryIndex, apiKey);

        // Build badge: "קייט סרפינג > ריבלים"
        const parts = [];
        if (json.sports?.length)     parts.push(json.sports.join(", "));
        if (json.categories?.length) parts.push(json.categories.join(", "));
        setAiBadge(parts.join(" > ") || null);

        setAiFilter(json);
      } catch (err) {
        console.warn("Smart search failed:", err);
        setAiFilter(null);
        setAiBadge(null);
      } finally {
        setAiLoading(false);
      }
    }, 400);
  }, [apiKey, categoryIndex]);

  const sports  = useMemo(
    () => [...new Set(products.map(p => p.sport).filter(Boolean))].sort(),
    [products]
  );
  const summary = useMemo(
    () => products.reduce((a, p) => { a[p.sport] = (a[p.sport] || 0) + 1; return a; }, {}),
    [products]
  );

  // Token scorer for AI-filtered results
  function scoreItem(p, aiJson) {
    let s = 0;
    const name = p.name.toLowerCase();
    for (const kw of (aiJson.keywords || [])) {
      const k = kw.toLowerCase();
      if (name.includes(k))                      s += 3;
      if (p.sku.toLowerCase().includes(k))       s += 2;
      if (p.category.toLowerCase().includes(k))  s += 1;
    }
    if (aiJson.brand && name.includes(aiJson.brand.toLowerCase())) s += 4;
    if (aiJson.size  && name.includes(aiJson.size.toLowerCase()))  s += 3;
    return s;
  }

  const visible = useMemo(() => {
    let pool = products;

    if (aiFilter) {
      // Step 1: Claude-driven sport/category filter
      if (aiFilter.sports?.length) {
        pool = pool.filter(p => aiFilter.sports.includes(p.sport));
      }
      if (aiFilter.categories?.length) {
        const narrowed = pool.filter(p =>
          aiFilter.categories.some(c => p.category.includes(c))
        );
        if (narrowed.length > 0) pool = narrowed;
      }
      if (pool.length === 0) pool = products; // safety fallback

      // Step 2: Token scoring + sort
      pool = [...pool].sort((a, b) => scoreItem(b, aiFilter) - scoreItem(a, aiFilter));
    } else {
      // Fallback: contains search
      if (sport)   pool = pool.filter(p => p.sport === sport);
      if (onSale)  pool = pool.filter(p => !!p.sale);
      if (inStock) pool = pool.filter(p => p.stock && !p.stock.includes("אזל"));
      if (search.trim()) {
        const q = search.trim().toLowerCase();
        pool = pool.filter(p =>
          p.name.toLowerCase().includes(q) ||
          p.sku.toLowerCase().includes(q)  ||
          p.category.toLowerCase().includes(q)
        );
      }
    }

    // Manual filters always apply on top
    if (aiFilter) {
      if (sport)   pool = pool.filter(p => p.sport === sport);
      if (onSale)  pool = pool.filter(p => !!p.sale);
      if (inStock) pool = pool.filter(p => p.stock && !p.stock.includes("אזל"));
    }

    // Sort (overrides AI scoring when explicitly chosen)
    if (sort === "price_asc")  pool = [...pool].sort((a, b) => priceNum(a.sale || a.regular) - priceNum(b.sale || b.regular));
    if (sort === "price_desc") pool = [...pool].sort((a, b) => priceNum(b.sale || b.regular) - priceNum(a.sale || a.regular));
    if (sort === "name")       pool = [...pool].sort((a, b) => a.name.localeCompare(b.name, "he"));

    return pool;
  }, [products, sport, onSale, inStock, search, sort, aiFilter]);

  // ── Upload screen ──
  if (!products.length) return (
    <div dir="rtl" style={{ fontFamily: "system-ui,-apple-system,sans-serif", minHeight: "100vh",
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      background: "#f8fafc", padding: 24 }}>
      <div style={{ fontSize: 48, marginBottom: 12 }}>🏄</div>
      <div style={{ fontWeight: 700, fontSize: 22, marginBottom: 4 }}>Yamit מוצרים</div>
      <div style={{ color: "#6b7280", fontSize: 14, marginBottom: 32 }}>העלה קובץ CSV מהסקריפט</div>
      <div
        onClick={() => fileRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); loadFile(e.dataTransfer.files[0]); }}
        style={{ border: `2.5px dashed ${dragging ? "#2563eb" : "#d1d5db"}`, borderRadius: 16,
          padding: "36px 48px", textAlign: "center", cursor: "pointer",
          background: dragging ? "#eff6ff" : "#fff", transition: "all .2s",
          maxWidth: 320, width: "100%" }}>
        <div style={{ fontSize: 36, marginBottom: 8 }}>📂</div>
        <div style={{ fontWeight: 600, fontSize: 15, color: dragging ? "#2563eb" : "#374151" }}>
          {loading ? "טוען…" : "לחץ או גרור CSV"}
        </div>
        <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>
          yamit_products_YYYY-MM-DD.csv
        </div>
      </div>
      <input ref={fileRef} type="file" accept=".csv" style={{ display: "none" }}
        onChange={e => loadFile(e.target.files[0])} />
    </div>
  );

  // ── Main screen ──
  return (
    <div dir="rtl" style={{ fontFamily: "system-ui,-apple-system,sans-serif",
      background: "#f8fafc", minHeight: "100vh" }}>

      {/* Settings modal */}
      {showSettings && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 100,
          display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
          onClick={() => setShowSettings(false)}>
          <div style={{ background: "#fff", borderRadius: 16, padding: 24, width: "100%",
            maxWidth: 360, boxShadow: "0 20px 60px rgba(0,0,0,.2)" }}
            onClick={e => e.stopPropagation()}>
            <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 16 }}>הגדרות</div>
            <label style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 6 }}>
              מפתח Claude API
            </label>
            <input
              type="password"
              value={apiKeyDraft}
              onChange={e => setApiKeyDraft(e.target.value)}
              placeholder="sk-ant-api03-..."
              style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db",
                borderRadius: 8, fontSize: 13, fontFamily: "monospace", direction: "ltr",
                boxSizing: "border-box" }} />
            <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 5 }}>
              נשמר מקומית בדפדפן · platform.anthropic.com
            </div>
            <button onClick={saveSettings}
              style={{ width: "100%", marginTop: 16, padding: "11px 0", background: "#2563eb",
                color: "#fff", border: "none", borderRadius: 10, fontWeight: 700,
                fontSize: 15, cursor: "pointer", fontFamily: "inherit" }}>
              שמור
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{ background: "#fff", borderBottom: "1px solid #e5e7eb",
        padding: "10px 14px", position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 22 }}>🏄</span>
          <span style={{ fontWeight: 700, fontSize: 17 }}>Yamit</span>
          <span style={{ fontSize: 12, color: "#9ca3af", marginRight: "auto" }}>
            {products.length} מוצרים
          </span>
          <button onClick={openSettings}
            style={{ fontSize: 12, color: apiKey ? "#2563eb" : "#9ca3af", background: "none",
              border: "1px solid #e5e7eb", borderRadius: 6, padding: "3px 8px", cursor: "pointer" }}>
            {apiKey ? "🔑 AI" : "⚙️"}
          </button>
          <button onClick={() => setProducts([])}
            style={{ fontSize: 12, color: "#6b7280", background: "none",
              border: "1px solid #e5e7eb", borderRadius: 6, padding: "3px 8px", cursor: "pointer" }}>
            CSV חדש
          </button>
        </div>

        {/* Search input */}
        <div style={{ position: "relative" }}>
          <input
            value={search}
            onChange={handleSearchChange}
            placeholder={apiKey ? "🤖 חפש בעברית או אנגלית: קייט ריבל 9, כנף 5m..." : "🔍  שם מוצר / מק״ט / קטגוריה"}
            style={{ width: "100%", padding: "9px 12px", fontSize: 15,
              border: `1px solid ${aiFilter ? "#2563eb" : "#d1d5db"}`,
              borderRadius: 10, boxSizing: "border-box", fontFamily: "inherit",
              direction: "rtl", outline: "none", paddingLeft: aiLoading ? 36 : 12 }} />
          {aiLoading && (
            <div style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)",
              fontSize: 14, color: "#6b7280" }}>
              🤔
            </div>
          )}
        </div>

        {/* AI badge */}
        {aiBadge && (
          <div style={{ marginTop: 6, fontSize: 12, color: "#2563eb",
            background: "#eff6ff", borderRadius: 6, padding: "3px 9px", display: "inline-block" }}>
            חיפוש ב: {aiBadge}
          </div>
        )}
        {!apiKey && (
          <div style={{ marginTop: 6, fontSize: 11, color: "#9ca3af" }}>
            ללא מפתח API — חיפוש מילוני בלבד.{" "}
            <span style={{ color: "#2563eb", cursor: "pointer" }} onClick={openSettings}>
              הגדר מפתח
            </span>{" "}
            לחיפוש חכם.
          </div>
        )}
      </div>

      {/* Filter bar */}
      <div style={{ padding: "10px 14px", background: "#fff", borderBottom: "1px solid #f0f0f0",
        display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        {sports.map(s => (
          <button key={s} onClick={() => setSport(f => f === s ? "" : s)}
            style={{ padding: "4px 11px", fontSize: 13, border: "1.5px solid",
              borderColor: SPORT_COLORS[s] || "#ccc",
              background: sport === s ? (SPORT_COLORS[s] || "#ccc") : "#fff",
              color: sport === s ? "#fff" : (SPORT_COLORS[s] || "#555"),
              borderRadius: 20, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" }}>
            {s} <span style={{ opacity: .75 }}>({summary[s] || 0})</span>
          </button>
        ))}
        {[["onSale", onSale, setOnSale, "🔥 מבצע"], ["inStock", inStock, setInStock, "✅ במלאי"]].map(([k, val, set, label]) => (
          <button key={k} onClick={() => set(v => !v)}
            style={{ padding: "4px 11px", fontSize: 13, border: "1.5px solid",
              borderColor: val ? "#2563eb" : "#d1d5db", background: val ? "#eff6ff" : "#fff",
              color: val ? "#2563eb" : "#6b7280", borderRadius: 20, cursor: "pointer",
              fontFamily: "inherit", whiteSpace: "nowrap" }}>{label}</button>
        ))}
        <select value={sort} onChange={e => setSort(e.target.value)}
          style={{ marginRight: "auto", fontSize: 13, border: "1px solid #d1d5db",
            borderRadius: 8, padding: "4px 8px", fontFamily: "inherit",
            background: "#fff", color: "#374151" }}>
          <option value="default">מיון: {aiFilter ? "רלוונטיות AI" : "ברירת מחדל"}</option>
          <option value="price_asc">מחיר: נמוך לגבוה</option>
          <option value="price_desc">מחיר: גבוה לנמוך</option>
          <option value="name">שם: א-ב</option>
        </select>
      </div>

      {/* Results count */}
      <div style={{ padding: "8px 14px", fontSize: 13, color: "#9ca3af" }}>
        {visible.length} תוצאות
        {visible.filter(p => p.sale).length > 0 && (
          <span style={{ color: "#ef4444", marginRight: 6 }}>
            · {visible.filter(p => p.sale).length} במבצע
          </span>
        )}
      </div>

      {/* Results */}
      <div style={{ padding: "0 14px 24px", display: "flex", flexDirection: "column", gap: 10 }}>
        {visible.length === 0
          ? <div style={{ textAlign: "center", padding: 40, color: "#9ca3af" }}>לא נמצאו מוצרים</div>
          : visible.slice(0, 300).map((p, i) => <ProductCard key={i} p={p} />)}
        {visible.length > 300 && (
          <div style={{ textAlign: "center", color: "#9ca3af", fontSize: 13, padding: 8 }}>
            מציג 300 מתוך {visible.length} — צמצם את החיפוש
          </div>
        )}
      </div>
    </div>
  );
}
