import html

import streamlit as st

from utils import load_products, get_price_for_tier, drive_thumbnail_url, apply_custom_css, format_currency, render_brand_header, render_top_navbar, render_contact_widget, gate_access, is_admin, LOGO_PATH

st.set_page_config(page_title="Catalog — Sena Product Catalog", page_icon=LOGO_PATH, layout="wide")
apply_custom_css()
render_contact_widget()
user_record = gate_access()
render_top_navbar(user_record, st.session_state.get("nav_pages", []))
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
    st.image(img_url, width="stretch")
    st.caption(name)


admin_mode = is_admin(user_record)
tier_options = ["Tier1", "Tier2", "Tier3", "Consumer", "Guest"]

util_col1, util_col2 = st.columns([3, 2], vertical_alignment="center")
with util_col1:
    if admin_mode:
        default_idx = tier_options.index(own_tier) if own_tier in tier_options else 0
        selected_tier = st.selectbox(
            "👑 Admin Preview — view pricing as tier", tier_options, index=default_idx,
        )
    else:
        selected_tier = own_tier

with util_col2:
    cart = st.session_state.get("cart", [])
    if cart:
        cart_total = sum(item["price"] * item["qty"] for item in cart)
        cart_label_col, cart_link_col = st.columns([2, 1], vertical_alignment="center")
        with cart_label_col:
            st.markdown(f"🛒 **{len(cart)} item(s)** — {format_currency(cart_total)}")
        with cart_link_col:
            st.page_link("pages/2_Cart.py", label="Go to Cart →", icon="🛒")
    else:
        st.caption("🛒 Cart is empty")

st.write("---")

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

            image_html = f'<img src="{img_url}" />' if img_url else '<span style="color:#A8916D;font-size:0.8rem;">No image</span>'
            size_html = f'<span class="size-badge">{size}</span>' if size else ""

            if show_margin:
                price_section = (
                    f'<div style="margin-top:10px;">'
                    f'<div style="font-size:0.72rem;font-weight:700;color:#059669;text-transform:uppercase;letter-spacing:0.03em;">Your Price</div>'
                    f'<div style="font-size:1.5rem;font-weight:800;color:#9C7A22;line-height:1.3;">{price_str}</div>'
                    f'<div style="font-size:0.72rem;font-weight:600;color:#A8916D;text-transform:uppercase;letter-spacing:0.03em;margin-top:8px;">Retail Price</div>'
                    f'<div style="font-size:0.95rem;font-weight:600;color:#A8916D;text-decoration:line-through;line-height:1.3;">{format_currency(consumer_price)}</div>'
                    f'</div>'
                )
            else:
                price_section = f'<div class="price-tag">{price_str}</div>'

            card_html = (
                f'<div class="product-card"><div style="padding:10px;">'
                f'<div class="product-image-wrap">{image_html}</div>'
                f'<div style="padding:12px 4px 4px 4px;">'
                f'<div style="font-weight:700;font-size:1.02rem;color:#3B2A1C;margin-bottom:2px;">{name}</div>'
                f'<div style="color:#6B5840;font-size:0.85rem;min-height:2.2em;margin-bottom:8px;">{description}</div>'
                f'<div class="size-badge-row">{size_html}</div>'
                f'{price_section}'
                f'</div></div></div>'
            )

            st.markdown(card_html, unsafe_allow_html=True)

            qty_key = f"qty_{product.get('ProductID')}"
            btn_col, qty_col = st.columns([1, 1])
            with btn_col:
                if img_url:
                    if st.button("🔍 View larger", key=f"viewlarge_{product.get('ProductID')}", width="stretch"):
                        show_large_image(img_url, name)
            with qty_col:
                qty = st.number_input("Qty", min_value=1, value=1, step=1, key=qty_key, label_visibility="collapsed")

            if st.button("Add to Cart", key=f"add_{product.get('ProductID')}", width="stretch"):
                existing_item = next(
                    (
                        cart_item for cart_item in st.session_state.cart
                        if cart_item["id"] == product.get("ProductID") and cart_item["tier"] == selected_tier
                    ),
                    None,
                )
                if existing_item:
                    existing_item["qty"] += qty
                else:
                    st.session_state.cart.append({
                        "id": product.get("ProductID"),
                        "name": product.get("Name"),
                        "size": product.get("Size/Measurement", ""),
                        "qty": qty,
                        "price": price,
                        "email": selected_email,
                        "tier": selected_tier,
                        "image_url": img_url,
                    })
                st.toast(f"Added {product.get('Name')} to cart", icon="🛒")
                st.rerun()

            st.write("")
