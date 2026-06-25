import json

import streamlit as st

from utils import generate_po_number, append_order_row, timestamp_now, apply_custom_css, format_currency, render_brand_header, render_top_navbar, render_contact_widget, gate_access, LOGO_PATH

st.set_page_config(page_title="Cart — Sena Product Catalog", page_icon=LOGO_PATH, layout="wide")
apply_custom_css()
render_contact_widget()
user_record = gate_access()
render_top_navbar(user_record, st.session_state.get("nav_pages", []))
render_brand_header("Cart & Checkout")

if "cart" not in st.session_state:
    st.session_state.cart = []

cart = st.session_state.cart

if not cart:
    st.info("Your cart is empty. Go to the Catalog page to add products.")
    st.page_link("pages/1_Catalog.py", label="← Back to Catalog", icon="📦")
    st.stop()

st.subheader("Items in cart")

for i, item in enumerate(cart):
    thumb_col, c1, c2, c3, c4, c5, c6, c7 = st.columns(
        [1.4, 1.8, 0.5, 0.6, 0.5, 1.1, 1.1, 0.6], vertical_alignment="center"
    )

    with thumb_col:
        image_url = item.get("image_url", "")
        if image_url:
            st.image(image_url, width=120)
        else:
            st.markdown(
                """<div style="width:120px;height:120px;border-radius:10px;background:#2B1D14;
                display:flex;align-items:center;justify-content:center;font-size:0.75rem;
                color:#D8CBB4;text-align:center;">No image</div>""",
                unsafe_allow_html=True,
            )

    c1.write(f"**{item['name']}**  \n_{item.get('size', '')}_")

    if c2.button("−", key=f"minus_{i}"):
        if item["qty"] > 1:
            item["qty"] -= 1
        st.rerun()

    c3.markdown(f"<div style='text-align:center;padding-top:6px;'>{item['qty']}</div>", unsafe_allow_html=True)

    if c4.button("+", key=f"plus_{i}"):
        item["qty"] += 1
        st.rerun()

    c5.write(f"{format_currency(item['price'])} each")
    c6.write(f"**{format_currency(item['price'] * item['qty'])}**")

    if c7.button("✕", key=f"remove_{i}"):
        cart.pop(i)
        st.rerun()

st.write("---")

total = sum(item["price"] * item["qty"] for item in cart)
st.markdown(f"## Total: {format_currency(total)}")

col_a, col_b = st.columns(2)
with col_a:
    if st.button("Clear Cart", width="stretch"):
        st.session_state.cart = []
        st.rerun()

with col_b:
    if st.button("✅ Submit Purchase Order", type="primary", width="stretch"):
        po_number = generate_po_number()
        timestamp = timestamp_now()
        email = cart[0].get("email", "guest@example.com")
        tier = cart[0].get("tier", "Guest")

        items_payload = [
            {"id": item["id"], "name": item["name"], "price": item["price"], "qty": item["qty"], "size": item.get("size", "")}
            for item in cart
        ]

        row = {
            "PO": po_number,
            "Timestamp": timestamp,
            "Email": email,
            "Tier": tier,
            "ItemsJSON": json.dumps(items_payload),
            "Total": total,
            "Status": "Confirmed",
            "Version": 1,
        }

        append_order_row(row)
        st.session_state.cart = []
        st.success(f"Purchase Order **{po_number}** submitted successfully!")
        st.balloons()
