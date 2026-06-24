import html

import streamlit as st

from utils import load_products, get_price_for_tier, drive_thumbnail_url, apply_custom_css, format_currency, render_brand_header, render_sidebar_logo, render_user_sidebar, gate_access, is_admin, LOGO_PATH

st.set_page_config(page_title="Catalog — Sena Product Catalog", page_icon=LOGO_PATH, layout="wide")
apply_custom_css()
render_sidebar_logo()
user_record = gate_access()
render_user_sidebar(user_record)
render_brand_header("Product Catalog")

selected_email = user_record.get("Email", "")
own_tier = user_record.get("Tier", "Guest")

products_df = load_products()


def clean(text) -> str:
    """Sanitize sheet text so it can't break the HTML card markup (strip newlines, escape quotes)."""
    if text is None:
        return ""
    return html.escape(str(text)).replace("\n", " ").replace("\r", " ").strip()


@st.dialog("Product Image", width="large")
def show_large_image(img_url: str, name: str):
    st.image(img_url, use_container_width=True)
    st.caption(name)


admin_mode = is_admin(user_record)

with st.sidebar:
    if admin_mode:
        st.header("👑 Admin Preview")
        tier_options = ["Tier1", "Tier2", "Tier3", "Consumer", "Guest"]
        default_idx = tier_options.index(own_tier) if own_tier in tier_options else 0
        selected_tier = st.selectbox("View pricing as tier", tier_options, index=default_idx)
        st.write("---")
    else:
        selected_tier = own_tier

    st.header("🛒 Cart")
    cart = st.session_state.get("cart", [])
    if cart:
        cart_total = sum(item["price"] * item["qty"] for item in cart)
        st.write(f"{len(cart)} item(s) — {format_currency(cart_total)}")
        st.page_link("pages/2_Cart.py", label="Go to Cart →", icon="🛒")
    else:
        st.write("Cart is empty")

search_term = st.text_input("🔍 Search products", placeholder="Search by name or description...")

if search_term:
    mask = (
        products_df["Name"].str.contains(search_term, case=False, na=False)
        | products_df["Description"].str.contains(search_term, case=False, na=False)
    )
    filtered_df = products_df[mask]
else:
    filtered_df = products_df

st.caption(f"{len(filtered_df)} product(s) found")

if "cart" not in st.session_state:
    st.session_state.cart = []

NUM_COLS = 3
rows = [filtered_df.iloc[i:i + NUM_COLS] for i in range(0, len(filtered_df), NUM_COLS)]

for row_df in rows:
    cols = st.columns(NUM_COLS)
    for col, (_, product) in zip(cols, row_df.iterrows()):
        with col:
            img_url = drive_thumbnail_url(product.get("ImageURL", ""))
            size = clean(product.get("Size/Measurement", ""))
            name = clean(product.get("Name", ""))
            description = clean(product.get("Description", ""))
            price = get_price_for_tier(product, selected_tier)
            price_str = format_currency(price)

            consumer_price = float(product.get("ConsumerPrice", 0) or 0)
            show_margin = selected_tier in ("Tier1", "Tier2", "Tier3") and consumer_price > price

            image_html = f'<img src="{img_url}" />' if img_url else '<span style="color:#9CA3AF;font-size:0.8rem;">No image</span>'
            size_html = f'<span class="size-badge">{size}</span>' if size else ""

            if show_margin:
                price_section = (
                    f'<div style="margin-top:10px;">'
                    f'<div style="font-size:0.72rem;font-weight:700;color:#059669;text-transform:uppercase;letter-spacing:0.03em;">Your Price</div>'
                    f'<div style="font-size:1.5rem;font-weight:800;color:#4F46E5;line-height:1.3;">{price_str}</div>'
                    f'<div style="font-size:0.72rem;font-weight:600;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.03em;margin-top:8px;">Retail Price</div>'
                    f'<div style="font-size:0.95rem;font-weight:600;color:#9CA3AF;text-decoration:line-through;line-height:1.3;">{format_currency(consumer_price)}</div>'
                    f'</div>'
                )
            else:
                price_section = f'<div class="price-tag">{price_str}</div>'

            card_html = (
                f'<div class="product-card"><div style="padding:10px;">'
                f'<div class="product-image-wrap">{image_html}</div>'
                f'<div style="padding:12px 4px 4px 4px;">'
                f'<div style="font-weight:700;font-size:1.02rem;color:#111827;margin-bottom:2px;">{name}</div>'
                f'<div style="color:#6B7280;font-size:0.85rem;min-height:2.2em;margin-bottom:8px;">{description}</div>'
                f'<div class="size-badge-row">{size_html}</div>'
                f'{price_section}'
                f'</div></div></div>'
            )

            st.markdown(card_html, unsafe_allow_html=True)

            qty_key = f"qty_{product.get('ProductID')}"
            btn_col, qty_col = st.columns([1, 1])
            with btn_col:
                if img_url:
                    if st.button("🔍 View larger", key=f"viewlarge_{product.get('ProductID')}", use_container_width=True):
                        show_large_image(img_url, name)
            with qty_col:
                qty = st.number_input("Qty", min_value=1, value=1, step=1, key=qty_key, label_visibility="collapsed")

            if st.button("Add to Cart", key=f"add_{product.get('ProductID')}", use_container_width=True):
                st.session_state.cart.append({
                    "id": product.get("ProductID"),
                    "name": product.get("Name"),
                    "size": product.get("Size/Measurement", ""),
                    "qty": qty,
                    "price": price,
                    "email": selected_email,
                    "tier": selected_tier,
                })
                st.toast(f"Added {product.get('Name')} to cart", icon="🛒")

            st.write("")
