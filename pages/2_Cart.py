import json

import streamlit as st

from utils import generate_po_number, append_order_row, timestamp_now, apply_custom_css

st.set_page_config(page_title="Cart — Sena Product Catalog", page_icon="🛒", layout="wide")
apply_custom_css()

st.title("🛒 Cart & Checkout")

if "cart" not in st.session_state:
    st.session_state.cart = []

cart = st.session_state.cart

if not cart:
    st.info("Your cart is empty. Go to the Catalog page to add products.")
    st.page_link("pages/1_Catalog.py", label="← Back to Catalog", icon="📦")
    st.stop()

st.subheader("Items in cart")

for i, item in enumerate(cart):
    c1, c2, c3, c4, c5 = st.columns([3, 1, 1.5, 1.5, 0.8])
    c1.write(f"**{item['name']}**  \n_{item.get('size', '')}_")
    c2.write(f"Qty: {item['qty']}")
    c3.write(f"${item['price']:,.2f} each")
    c4.write(f"**${item['price'] * item['qty']:,.2f}**")
    if c5.button("✕", key=f"remove_{i}"):
        cart.pop(i)
        st.rerun()

st.write("---")

total = sum(item["price"] * item["qty"] for item in cart)
st.markdown(f"## Total: ${total:,.2f}")

col_a, col_b = st.columns(2)
with col_a:
    if st.button("Clear Cart", use_container_width=True):
        st.session_state.cart = []
        st.rerun()

with col_b:
    if st.button("✅ Submit Purchase Order", type="primary", use_container_width=True):
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
