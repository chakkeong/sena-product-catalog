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
    get_price_for_tier,
    is_admin,
    LOGO_PATH,
)

st.set_page_config(page_title="Showcase — Sena Product Catalog", page_icon=LOGO_PATH, layout="wide")
render_contact_widget()
user_record = gate_access()
render_top_navbar(user_record, st.session_state.get("nav_pages", []))

selected_email = user_record.get("Email", "")
own_tier = user_record.get("Tier", "Guest")

# Admins often have a "Tier" value (e.g. "Admin") that isn't one of the
# actual pricing tiers, which would otherwise silently fall back to
# Consumer pricing below. Catalog already works around this with a preview
# dropdown — mirror that here so Showcase and Catalog always agree.
if is_admin(user_record):
    tier_options = ["Tier1", "Tier2", "Tier3", "Consumer", "Guest"]
    default_idx = tier_options.index(own_tier) if own_tier in tier_options else 0
    own_tier = st.selectbox(
        "👑 Admin Preview — view Showcase pricing as tier", tier_options, index=default_idx,
    )

try:
    products_df = load_products()
except Exception as e:
    products_df = None
    st.error(f"Could not load products from the Google Sheet: {e}")

# ---------------------------------------------------------------------------
# Bridge for "Add to Cart" clicks coming from the showcase grid below. That
# grid renders inside a sandboxed components.html iframe, which can read/
# write the real page's DOM (window.parent.document) but is NOT allowed to
# navigate it — browsers treat those as separate permissions. So instead of
# reloading the page with a query param, we render one real (hidden) button
# per product further down, and the iframe's button finds and .click()s the
# matching one — a plain DOM operation with no cross-origin restriction.
# ---------------------------------------------------------------------------

def add_product_to_cart(product_id: str):
    if products_df is None or "ProductID" not in products_df.columns:
        return
    match = products_df[products_df["ProductID"].astype(str) == str(product_id)]
    if match.empty:
        return
    row = match.iloc[0]
    price = get_price_for_tier(row, own_tier)
    img_url = drive_thumbnail_url(str(row.get("ImageURL", "") or ""))

    if "cart" not in st.session_state:
        st.session_state.cart = []

    existing_item = next(
        (
            item for item in st.session_state.cart
            if item["id"] == product_id and item["tier"] == own_tier
        ),
        None,
    )
    if existing_item:
        existing_item["qty"] += 1
    else:
        st.session_state.cart.append({
            "id": product_id,
            "name": row.get("Name", ""),
            "size": row.get("Size/Measurement", ""),
            "qty": 1,
            "price": price,
            "email": selected_email,
            "tier": own_tier,
            "image_url": img_url,
        })
    st.toast(f"Added {row.get('Name', 'item')} to cart", icon="🛒")

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
                "id": str(row.get("ProductID", "")),
                "name": str(row.get("Name", "")),
                "size": str(row.get("Size/Measurement", "") or ""),
                "price": get_price_for_tier(row, own_tier),
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

# One real button per unique product. The showcase grid's JS below finds
# the matching one by its exact label text and calls .click() on it — a
# normal DOM operation, sidestepping the cross-origin navigation
# restriction entirely. Hidden via a marker + CSS sibling selector for a
# real display:none (st.container(height=1) only clips visually, it
# doesn't actually hide the content — confirmed by testing).
unique_products_by_id = {}
for concept in concepts_data:
    for p in concept["products"]:
        unique_products_by_id[p["id"]] = p

st.markdown('<div id="sena-addcart-bridge-marker"></div>', unsafe_allow_html=True)
for product_id, product in unique_products_by_id.items():
    if st.button(f"ADDCARTBTN-{product_id}", key=f"hidden_addcart_{product_id}"):
        add_product_to_cart(product_id)
st.markdown(
    '<style>#sena-addcart-bridge-marker ~ div[data-testid="stButton"] '
    '{ display: none !important; }</style>',
    unsafe_allow_html=True,
)


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
  .wrap { max-width: 1100px; margin: 0 auto; padding: 0 24px; position: relative; }

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
  .hero-img-wrap { position: relative; }
  .hero-img, .grain {
    width: 100%; aspect-ratio: 16 / 10; height: auto;
    border-radius: 12px; margin-bottom: 16px; object-fit: contain;
    object-position: center; background: #2B1D14; display: block;
  }
  .hero-expand-btn {
    position: absolute; bottom: 28px; right: 12px; width: 36px; height: 36px;
    border-radius: 50%; border: none; background: rgba(43, 29, 20, 0.75);
    color: #F3EAD8; display: flex; align-items: center; justify-content: center;
    cursor: pointer; backdrop-filter: blur(2px); transition: background 0.15s;
  }
  .hero-expand-btn:hover { background: #C9A227; color: #2B1D14; }
  .hero-expand-btn:focus-visible { outline: 2px solid #C9A227; outline-offset: 2px; }
  .concept-title { font-size: 1.4rem; margin-bottom: 8px; }
  .concept-mood { color: #D8CBB4; font-size: 0.9rem; }

  /* Lightbox: the backdrop is "fixed" so it dims whatever's currently
     visible (this page has no internal scrollbar of its own, so "fixed"
     here just means "the whole rendered area"). The popup itself is
     "absolute" relative to .wrap instead — anchored to the photo's own
     position in the page, so it appears exactly where you're already
     looking no matter how far down the page you've scrolled. */
  .lightbox-backdrop {
    position: fixed; inset: 0; background: rgba(20, 13, 8, 0.92);
    z-index: 9000; cursor: pointer;
  }
  .lightbox-popup {
    position: absolute; left: 50%; transform: translateX(-50%);
    width: min(92%, 820px); z-index: 9001;
  }
  .lightbox-popup img {
    width: 100%; height: auto; max-height: 640px; object-fit: contain;
    border-radius: 10px; background: #2B1D14; display: block;
  }
  .lightbox-close-btn {
    position: absolute; top: -44px; right: 0; width: 36px; height: 36px;
    border-radius: 50%; border: none; background: rgba(43, 29, 20, 0.85);
    color: #F3EAD8; cursor: pointer; display: flex; align-items: center;
    justify-content: center; font-size: 1.1rem;
  }
  .lightbox-close-btn:hover { background: #C9A227; color: #2B1D14; }

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
    .concept-side { width: 380px; }
  }

  /* --- Laptops and up: roomier card, wider side panel, 3-up products --- */
  @media (min-width: 1024px) {
    .wrap { max-width: 1280px; }
    .concept-card { padding: 32px; padding-bottom: 64px; }
    .concept-side { width: 460px; }
    .products { grid-template-columns: 1fr 1fr 1fr; gap: 18px; }
    .concept-title { font-size: 1.5rem; }
  }
  .add-cart-btn {
    width: 100%; margin-top: 12px; padding: 10px 0; border-radius: 8px; border: none;
    background: #C9A227; color: #2B1D14; font-weight: 700; font-size: 0.85rem;
    cursor: pointer; transition: background 0.15s;
  }
  .add-cart-btn:hover { background: #E0B72E; }
  .add-cart-btn:disabled { background: #5C3A21; color: #D8CBB4; cursor: default; }
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

    const EXPAND_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>';

    // Opening via a real Drive page navigation (even a "public" link) can
    // trigger Google's account-chooser screen when multiple Google accounts
    // are signed into the browser — that's a Drive/account-switcher quirk,
    // not a permissions problem. A same-page popup avoids navigation
    // entirely, so the prompt never has a chance to appear.
    const heroBlock = concept.hero_image
      ? `<div class="hero-img-wrap">
          <img class="hero-img" src="${concept.hero_image}" loading="lazy" decoding="async" alt="${concept.label} concept" />
          <button class="hero-expand-btn" data-src="${concept.hero_image}" aria-label="Enlarge photo">${EXPAND_SVG}</button>
        </div>`
      : `<div class="grain" style="background:#5C3A21;"></div>`;

    const productsBlock = concept.products.length
      ? concept.products.map(p => `
          <div class="product-card">
            ${p.image
              ? `<img class="product-thumb" src="${p.image}" loading="lazy" decoding="async" alt="${p.name}" />`
              : `<div class="product-thumb-placeholder">No image</div>`}
            <div class="product-name display">${p.name}</div>
            <div class="product-spec">${p.size || '&nbsp;'}</div>
            <div class="product-bottom">
              <div class="product-price display">${fmtRM(p.price)}</div>
            </div>
            <button class="add-cart-btn" data-id="${p.id}">Add to Cart</button>
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

    const expandBtn = cardEl.querySelector(".hero-expand-btn");
    if (expandBtn) {
      expandBtn.addEventListener("click", () => openLightbox(expandBtn));
    }

    // Showcase renders inside a sandboxed iframe: it can read/write the
    // real page's DOM (window.parent.document) but is NOT allowed to
    // navigate it — confirmed via testing, those are separate browser
    // permissions. So instead of navigating, find the real (hidden)
    // Streamlit button rendered for this exact product and .click() it —
    // a plain DOM operation with no cross-origin restriction at all.
    cardEl.querySelectorAll(".add-cart-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const targetLabel = `ADDCARTBTN-${btn.dataset.id}`;
        const parentButtons = window.parent.document.querySelectorAll("button");
        let matched = null;
        for (const b of parentButtons) {
          if (b.textContent.trim() === targetLabel) { matched = b; break; }
        }
        if (matched) {
          btn.disabled = true;
          btn.textContent = "Added ✓";
          matched.click();
          setTimeout(() => { btn.disabled = false; btn.textContent = "Add to Cart"; }, 1200);
        } else {
          alert("Add to cart: could not find the matching item — please refresh and try again.");
        }
      });
    });
  }

  function openLightbox(anchorEl) {
    closeLightbox();

    const wrapEl = document.querySelector(".wrap");
    const wrapRect = wrapEl.getBoundingClientRect();
    const anchorRect = anchorEl.closest(".hero-img-wrap").getBoundingClientRect();
    const topOffset = anchorRect.top - wrapRect.top;

    const backdrop = document.createElement("div");
    backdrop.className = "lightbox-backdrop";
    backdrop.id = "sena-lightbox-backdrop";
    backdrop.addEventListener("click", closeLightbox);

    const popup = document.createElement("div");
    popup.className = "lightbox-popup";
    popup.id = "sena-lightbox-popup";
    popup.style.top = `${Math.max(topOffset, 0)}px`;
    popup.innerHTML = `
      <button class="lightbox-close-btn" aria-label="Close">✕</button>
      <img src="${anchorEl.dataset.src}" alt="" />
    `;
    popup.querySelector(".lightbox-close-btn").addEventListener("click", closeLightbox);

    wrapEl.appendChild(backdrop);
    wrapEl.appendChild(popup);
    document.addEventListener("keydown", onLightboxKeydown);
  }

  function closeLightbox() {
    document.getElementById("sena-lightbox-backdrop")?.remove();
    document.getElementById("sena-lightbox-popup")?.remove();
    document.removeEventListener("keydown", onLightboxKeydown);
  }

  function onLightboxKeydown(e) {
    if (e.key === "Escape") closeLightbox();
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
