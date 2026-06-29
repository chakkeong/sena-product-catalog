import html
import json

import streamlit as st
import streamlit.components.v1 as components

from utils import (
    gate_access,
    render_top_navbar,
    render_contact_widget,
    load_products,
    drive_thumbnail_url,
    load_showcase_content,
    load_concepts,
    LOGO_PATH,
)

st.set_page_config(page_title="Showcase — Sena Product Catalog", page_icon=LOGO_PATH, layout="wide")
render_contact_widget()
user_record = gate_access()
render_top_navbar(user_record, st.session_state.get("nav_pages", []))

# ---------------------------------------------------------------------------
# Pull real products from the Google Sheet and group them by concept.
# A product belongs to a concept if its Name contains that concept's keyword
# (e.g. "Sofa 3 Seater Homey" matches the "Homey" concept). The keyword
# mapping stays in code since it's structural; the label/mood/photo for each
# concept (and the hero text above) come from the Showcase sheet tab, which
# is editable from the Dashboard.
# ---------------------------------------------------------------------------

content = load_showcase_content()
concept_defs = load_concepts()

try:
    products_df = load_products()
except Exception as e:
    products_df = None
    st.error(f"Could not load products from the Google Sheet: {e}")

concepts_data = []
if products_df is not None and not products_df.empty and "Name" in products_df.columns:
    for cdef in concept_defs:
        keyword = cdef["keyword"] or cdef["id"]
        matches = products_df[
            products_df["Name"].astype(str).str.contains(keyword, case=False, na=False)
        ]
        products = []
        for _, row in matches.iterrows():
            products.append({
                "name": str(row.get("Name", "")),
                "size": str(row.get("Size/Measurement", "") or ""),
                "price": float(row.get("ConsumerPrice", 0) or 0),
                "image": drive_thumbnail_url(str(row.get("ImageURL", "") or "")),
            })
        concepts_data.append({
            "id": cdef["id"],
            "label": cdef["label"] or cdef["id"].title(),
            "mood": cdef["mood"],
            "hero_image": cdef["hero_image"] or (products[0]["image"] if products else ""),
            "products": products,
        })

CONCEPTS_JSON = json.dumps(concepts_data)

SHOWCASE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');

  * { box-sizing: border-box; }
  body {
    margin: 0;
    background-color: #2B1D14;
    color: #F3EAD8;
    font-family: 'Work Sans', sans-serif;
  }
  .display { font-family: 'Fraunces', serif; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 0 24px; }

  header.nav { display: flex; align-items: center; padding-top: 32px; }
  .logo { font-size: 1.25rem; letter-spacing: 0.02em; }
  .logo-sub { color: #C9A66B; font-size: 10px; letter-spacing: 0.25em; text-transform: uppercase; }

  .hero { padding: 56px 0 40px; }
  .eyebrow { color: #C9A227; font-size: 0.75rem; letter-spacing: 0.25em; text-transform: uppercase; margin-bottom: 20px; }
  h1 { font-size: clamp(1.75rem, 5vw + 1rem, 2.6rem); line-height: 1.1; margin: 0 0 24px; max-width: 640px; }
  .lead { color: #D8CBB4; font-size: 1.05rem; max-width: 540px; margin: 0; }

  .tabs { display: flex; gap: 12px; flex-wrap: wrap; padding: 0 0 32px; }
  .tab {
    padding: 10px 20px; border-radius: 999px; font-size: 0.9rem; font-weight: 500;
    background: transparent; color: #D8CBB4; border: 1px solid #5C3A21; cursor: pointer;
    display: inline-flex; align-items: center; gap: 8px; transition: background 0.15s, color 0.15s;
  }
  .tab.active { background: #C9A227; color: #2B1D14; border-color: #C9A227; }
  .tab:focus-visible { outline: 2px solid #C9A227; outline-offset: 3px; }

  .concept-card {
    background: #3A2A1C; border: 1px solid #5C3A21; border-radius: 16px;
    padding: 20px; display: flex; flex-direction: column; gap: 24px; padding-bottom: 40px;
  }
  .concept-side { width: 100%; flex-shrink: 0; }
  .hero-img, .grain {
    width: 100%; aspect-ratio: 16 / 10; height: auto;
    border-radius: 12px; margin-bottom: 16px; object-fit: contain;
    object-position: center; background: #2B1D14; display: block;
  }
  .concept-title { font-size: 1.4rem; margin-bottom: 8px; }
  .concept-mood { color: #D8CBB4; font-size: 0.9rem; }

  .products {
    flex: 1; min-width: 0; display: grid;
    grid-template-columns: 1fr; gap: 14px;
  }
  .product-card { background: #2B1D14; border: 1px solid #5C3A21; border-radius: 12px; padding: 16px; }
  .product-thumb, .product-thumb-placeholder {
    width: 100%; aspect-ratio: 4 / 3; height: auto;
    object-fit: cover; border-radius: 8px; margin-bottom: 14px; display: block;
  }
  .product-thumb-placeholder {
    background: #3A2A1C; display: flex; align-items: center; justify-content: center;
    color: #D8CBB4; font-size: 0.75rem;
  }

  /* --- Small phones: tighten card padding a touch --- */
  @media (max-width: 380px) {
    .concept-card { padding: 16px; }
  }

  /* --- Large phones / small tablets: 2-up product grid --- */
  @media (min-width: 540px) {
    .products { grid-template-columns: 1fr 1fr; gap: 16px; }
  }

  /* --- Tablets and up: hero + products sit side-by-side --- */
  @media (min-width: 768px) {
    .concept-card { flex-direction: row; gap: 32px; padding: 28px; padding-bottom: 56px; }
    .concept-side { width: 320px; }
  }

  /* --- Laptops and up: roomier card, wider side panel, 3-up products --- */
  @media (min-width: 1024px) {
    .concept-card { padding: 32px; padding-bottom: 64px; }
    .concept-side { width: 360px; }
    .products { grid-template-columns: 1fr 1fr 1fr; gap: 18px; }
    .concept-title { font-size: 1.5rem; }
  }
  .badge {
    display: inline-block; font-size: 0.75rem; padding: 4px 10px; border-radius: 999px;
    background: #4B5D45; color: #F3EAD8; margin-bottom: 16px;
  }
  .product-name { font-size: 1.1rem; margin-bottom: 4px; }
  .product-spec { font-size: 0.75rem; color: #C9A66B; margin-bottom: 16px; }
  .product-bottom { display: flex; align-items: flex-end; justify-content: space-between; }
  .product-price { font-size: 1.5rem; color: #C9A227; }
  .view-link { color: #C9A227; font-size: 0.9rem; font-weight: 500; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
  .empty-note { color: #D8CBB4; font-size: 0.9rem; padding: 20px 0; }

  footer { padding: 48px 0; border-top: 1px solid #3A2A1C; margin-top: 24px; }
  .footer-inner { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; flex-wrap: wrap; }
  .footer-name { font-size: 1.1rem; margin-bottom: 4px; }
  .footer-addr, .footer-contact { color: #D8CBB4; font-size: 0.9rem; }
  .footer-contact { text-align: right; }
  .footer-reg { font-size: 0.75rem; color: #8C6239; margin-top: 8px; }
</style>
</head>
<body>
  <div class="wrap">
    <header class="nav">
      <div>
        <div class="logo display">SENA</div>
        <div class="logo-sub">Home Solution</div>
      </div>
    </header>

    <section class="hero">
      <div class="eyebrow">__HERO_EYEBROW__</div>
      <h1 class="display">__HERO_HEADLINE__</h1>
      <p class="lead">__HERO_LEAD__</p>
    </section>

    <section>
      <div class="tabs" id="tabs"></div>
      <div class="concept-card" id="concept-card"></div>
    </section>

    <footer>
      <div class="footer-inner">
        <div>
          <div class="footer-name display">Sena Home Solution</div>
          <div class="footer-addr">
            AZ A3A-02, Level 3A, Block A, Anzen Business Park,<br/>
            Jalan 4/37A, Taman Industri Bukit Maluri,<br/>
            52100 Kepong, Kuala Lumpur
          </div>
        </div>
        <div class="footer-contact">
          <div>+60 13-633 8923</div>
          <div>lee@senahome.online</div>
          <div>www.senahome.online</div>
          <div class="footer-reg">Reg. No: 202503169281 (NIS0310717-X)</div>
        </div>
      </div>
    </footer>
  </div>

<script>
  const CONCEPTS = __CONCEPTS_JSON__;

  const CHECK_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';

  function fmtRM(v) { return "RM " + Number(v).toLocaleString("en-MY"); }

  let activeId = CONCEPTS.length ? CONCEPTS[0].id : null;

  function renderTabs() {
    const tabsEl = document.getElementById("tabs");
    tabsEl.innerHTML = CONCEPTS.map(c => `
      <button class="tab ${c.id === activeId ? 'active' : ''}" data-id="${c.id}">
        ${c.id === activeId ? CHECK_SVG : ''} ${c.label}
      </button>
    `).join("");
    tabsEl.querySelectorAll(".tab").forEach(btn => {
      btn.addEventListener("click", () => {
        activeId = btn.dataset.id;
        renderTabs();
        renderConceptCard();
      });
    });
  }

  function renderConceptCard() {
    const concept = CONCEPTS.find(c => c.id === activeId);
    const cardEl = document.getElementById("concept-card");
    if (!concept) {
      cardEl.innerHTML = '<div class="empty-note">No concepts found yet. Add one from the Showcase Page Editor on the Dashboard.</div>';
      return;
    }

    const heroBlock = concept.hero_image
      ? `<img class="hero-img" src="${concept.hero_image}" loading="lazy" decoding="async" alt="${concept.label} concept" />`
      : `<div class="grain" style="background:#5C3A21;"></div>`;

    const productsBlock = concept.products.length
      ? concept.products.map(p => `
          <div class="product-card">
            ${p.image
              ? `<img class="product-thumb" src="${p.image}" loading="lazy" decoding="async" alt="${p.name}" />`
              : `<div class="product-thumb-placeholder">No image</div>`}
            <span class="badge">Ready to ship</span>
            <div class="product-name display">${p.name}</div>
            <div class="product-spec">${p.size || '&nbsp;'}</div>
            <div class="product-bottom">
              <div class="product-price display">${fmtRM(p.price)}</div>
            </div>
          </div>
        `).join("")
      : '<div class="empty-note">No ready-made pieces tagged for this concept yet.</div>';

    cardEl.innerHTML = `
      <div class="concept-side">
        ${heroBlock}
        <div class="concept-title display">${concept.label}</div>
        <div class="concept-mood">${concept.mood}</div>
      </div>
      <div class="products">
        ${productsBlock}
      </div>
    `;
  }

  renderTabs();
  renderConceptCard();

  // Auto-resize this iframe to match its real content height, so the page
  // never has two competing scroll areas (which feels "draggy" on mobile,
  // since touch has to decide whether to scroll the iframe or the page).
  function resizeToContent() {
    if (window.frameElement) {
      window.frameElement.style.height = document.documentElement.scrollHeight + 'px';
    }
  }
  window.addEventListener('load', resizeToContent);
  new ResizeObserver(resizeToContent).observe(document.body);
  // Concept switches change content height without firing 'load' or a
  // size-changing layout shift the observer always catches in time, so
  // nudge it again shortly after every tab click too.
  document.getElementById('tabs').addEventListener('click', () => {
    setTimeout(resizeToContent, 50);
  });
  resizeToContent();
</script>
</body>
</html>
"""

SHOWCASE_HTML = (
    SHOWCASE_HTML_TEMPLATE
    .replace("__CONCEPTS_JSON__", CONCEPTS_JSON)
    .replace("__HERO_EYEBROW__", html.escape(content.get("hero_eyebrow", "")))
    .replace("__HERO_HEADLINE__", html.escape(content.get("hero_headline", "")))
    .replace("__HERO_LEAD__", html.escape(content.get("hero_lead", "")))
)

components.html(SHOWCASE_HTML, height=600, scrolling=False)
