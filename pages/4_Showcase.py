import streamlit as st
import streamlit.components.v1 as components

from utils import gate_access, render_top_navbar, render_contact_widget, LOGO_PATH

st.set_page_config(page_title="Showcase — Sena Product Catalog", page_icon=LOGO_PATH, layout="wide")
render_contact_widget()
user_record = gate_access()
render_top_navbar(user_record, st.session_state["nav_pages"])

SHOWCASE_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');

  * { box-sizing: border-box; }
  body {
    margin: 0;
    background-color: #EAE0CC;
    color: #3B2A1C;
    font-family: 'Work Sans', sans-serif;
  }
  .display { font-family: 'Fraunces', serif; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 0 24px; }

  header.nav { display: flex; align-items: center; justify-content: space-between; padding-top: 32px; }
  .logo { font-size: 1.25rem; letter-spacing: 0.02em; }
  .logo-sub { color: #8C6B3D; font-size: 10px; letter-spacing: 0.25em; text-transform: uppercase; }
  nav a { color: #6B5840; text-decoration: none; margin-left: 28px; font-size: 0.9rem; }
  nav a:focus-visible { outline: 2px solid #C9A227; outline-offset: 3px; }

  .hero { padding: 56px 0 40px; }
  .eyebrow { color: #9C7A22; font-size: 0.75rem; letter-spacing: 0.25em; text-transform: uppercase; margin-bottom: 20px; }
  h1 { font-size: 2.6rem; line-height: 1.08; margin: 0 0 24px; max-width: 640px; }
  .lead { color: #6B5840; font-size: 1.05rem; max-width: 540px; margin: 0; }

  .tabs { display: flex; gap: 12px; flex-wrap: wrap; padding: 0 0 32px; }
  .tab {
    padding: 10px 20px; border-radius: 999px; font-size: 0.9rem; font-weight: 500;
    background: transparent; color: #6B5840; border: 1px solid #DCCBA8; cursor: pointer;
    display: inline-flex; align-items: center; gap: 8px; transition: background 0.15s, color 0.15s;
  }
  .tab.active { background: #C9A227; color: #2B1D14; border-color: #C9A227; }
  .tab:focus-visible { outline: 2px solid #C9A227; outline-offset: 3px; }

  .concept-card {
    background: #F1E8D4; border: 1px solid #DCCBA8; border-radius: 16px;
    padding: 32px; display: flex; gap: 32px; flex-wrap: wrap; padding-bottom: 64px;
  }
  .concept-side { width: 240px; flex-shrink: 0; }
  .grain { width: 100%; height: 150px; border-radius: 12px; margin-bottom: 16px; }
  .concept-title { font-size: 1.5rem; margin-bottom: 8px; }
  .concept-mood { color: #6B5840; font-size: 0.9rem; }

  .products { flex: 1; min-width: 260px; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 640px) { .products { grid-template-columns: 1fr; } }
  .product-card { background: #FBF7EC; border: 1px solid #DCCBA8; border-radius: 12px; padding: 20px; }
  .badge {
    display: inline-block; font-size: 0.75rem; padding: 4px 10px; border-radius: 999px;
    background: #4B5D45; color: #F3EAD8; margin-bottom: 16px;
  }
  .product-name { font-size: 1.1rem; margin-bottom: 4px; }
  .product-spec { font-size: 0.75rem; color: #8C6B3D; margin-bottom: 16px; }
  .product-bottom { display: flex; align-items: flex-end; justify-content: space-between; }
  .product-price { font-size: 1.5rem; }
  .view-link { color: #9C7A22; font-size: 0.9rem; font-weight: 500; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }

  .collection { padding: 64px 0; border-top: 1px solid #DCCBA8; }
  .collection-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 40px; }
  .collection-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
  @media (max-width: 900px) { .collection-grid { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 560px) { .collection-grid { grid-template-columns: 1fr; } }
  .item-card { background: #F1E8D4; border: 1px solid #DCCBA8; border-radius: 12px; padding: 20px; transition: transform 0.15s; }
  .item-card:hover { transform: translateY(-4px); }
  .item-grain { width: 100%; height: 112px; border-radius: 8px; margin-bottom: 16px; background-color: #6B4226; background-image: repeating-linear-gradient(115deg, #5C3A21 0px, #5C3A21 2px, transparent 2px, transparent 10px); }
  .item-kind { font-size: 0.75rem; color: #8C6B3D; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
  .item-name { font-size: 1.1rem; margin-bottom: 4px; }
  .item-note { font-size: 0.9rem; color: #6B5840; margin-bottom: 12px; }
  .item-price { font-size: 0.9rem; font-weight: 600; color: #9C7A22; }

  footer { padding: 48px 0; border-top: 1px solid #DCCBA8; }
  .footer-inner { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; flex-wrap: wrap; }
  .footer-name { font-size: 1.1rem; margin-bottom: 4px; }
  .footer-addr, .footer-contact { color: #6B5840; font-size: 0.9rem; }
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
      <nav>
        <a href="#concepts">Concepts</a>
        <a href="#collection">Collection</a>
        <a href="#visit">Visit</a>
      </nav>
    </header>

    <section class="hero">
      <div class="eyebrow">Ready-made, by concept</div>
      <h1 class="display">Every piece is finished and ready. You're choosing a feeling, not a spec sheet.</h1>
      <p class="lead">Sena doesn't build to order — we hold three ready-made concepts in stock, each with its own wood, fabric, and mood already decided. Pick the one that's you.</p>
    </section>

    <section id="concepts">
      <div class="tabs" id="tabs"></div>
      <div class="concept-card" id="concept-card"></div>
    </section>

    <section class="collection" id="collection">
      <div class="collection-head">
        <h2 class="display" style="font-size:1.8rem;margin:0;">The Collection</h2>
        <span style="color:#8C6B3D;font-size:0.9rem;">4 pieces in stock</span>
      </div>
      <div class="collection-grid">
        <div class="item-card">
          <div class="item-grain"></div>
          <div class="item-kind">3-seater</div>
          <div class="item-name display">The Maluri Sofa</div>
          <div class="item-note">Walnut frame, deep-seat cushions</div>
          <div class="item-price">RM 4,200</div>
        </div>
        <div class="item-card">
          <div class="item-grain"></div>
          <div class="item-kind">6-seater</div>
          <div class="item-name display">Anzen Dining Table</div>
          <div class="item-note">Solid oak, hand-waxed finish</div>
          <div class="item-price">RM 3,850</div>
        </div>
        <div class="item-card">
          <div class="item-grain"></div>
          <div class="item-kind">lounge</div>
          <div class="item-name display">Kepong Armchair</div>
          <div class="item-note">Teak frame, brass stud trim</div>
          <div class="item-price">RM 2,100</div>
        </div>
        <div class="item-card">
          <div class="item-grain"></div>
          <div class="item-kind">entryway</div>
          <div class="item-name display">Bukit Console</div>
          <div class="item-note">Oak, brass inlay handles</div>
          <div class="item-price">RM 1,650</div>
        </div>
      </div>
    </section>

    <footer id="visit">
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
  const CONCEPTS = [
    {
      id: "homey", label: "Homey",
      mood: "Warm, deep-seated pieces for a living room you don't want to leave.",
      swatch: "#6B4226", grain: "#52301B",
      products: [
        { name: "Sofa 3-Seater Homey", spec: "Walnut frame · Linen upholstery · 210 × 90 × 85 cm", price: 2000 },
        { name: "Coffee Table Homey", spec: "Walnut · Hand-waxed finish · 110 × 55 × 42 cm", price: 680 },
      ],
    },
    {
      id: "insta", label: "Insta",
      mood: "Clean lines and a light palette — built to photograph as well as it sits.",
      swatch: "#C9A66B", grain: "#B08F52",
      products: [
        { name: "Sofa 3-Seater Insta", spec: "Oak frame · Bouclé upholstery · 215 × 88 × 80 cm", price: 2000 },
        { name: "Side Table Insta", spec: "Oak · Matte finish · 45 × 45 × 50 cm", price: 420 },
      ],
    },
    {
      id: "modern", label: "Modern",
      mood: "Tight, structured silhouettes for smaller spaces that still feel deliberate.",
      swatch: "#8C6239", grain: "#6E4A28",
      products: [
        { name: "Sofa 2-Seater Modern", spec: "Teak frame · Structured weave · 175 × 85 × 78 cm", price: 1200 },
        { name: "Console Modern", spec: "Teak · Brass inlay handles · 120 × 35 × 75 cm", price: 950 },
      ],
    },
  ];

  const CHECK_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';
  const ARROW_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>';

  function fmtRM(v) { return "RM " + v.toLocaleString("en-MY"); }

  function grainStyle(color, grain) {
    return `background-color:${color};background-image:repeating-linear-gradient(115deg, ${grain} 0px, ${grain} 2px, transparent 2px, transparent 9px);`;
  }

  let activeId = "homey";

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
    cardEl.innerHTML = `
      <div class="concept-side">
        <div class="grain" style="${grainStyle(concept.swatch, concept.grain)}"></div>
        <div class="concept-title display">${concept.label}</div>
        <div class="concept-mood">${concept.mood}</div>
      </div>
      <div class="products">
        ${concept.products.map(p => `
          <div class="product-card">
            <span class="badge">Ready to ship</span>
            <div class="product-name display">${p.name}</div>
            <div class="product-spec">${p.spec}</div>
            <div class="product-bottom">
              <div class="product-price display">${fmtRM(p.price)}</div>
              <a class="view-link" href="#collection">View ${ARROW_SVG}</a>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  }

  renderTabs();
  renderConceptCard();
</script>
</body>
</html>
"""

components.html(SHOWCASE_HTML, height=1900, scrolling=True)
