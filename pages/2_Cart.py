import streamlit as st

from utils import load_orders, generate_po_number, append_order_rows, timestamp_now

st.set_page_config(page_title="Cart — Sena Product Catalog", page_icon="🛒", layout="wide")

st.title("🛒 Cart & Checkout")

if "cart" not in st.session_state:
    st.session_state.cart = []

cart = st.session_state.cart

if not cart:
    st.info("Your cart is empty. Go to the Catalog page to add products.")
    st.page_link("pages/1_Catalog.py", label="← Back to Catalog", icon="📦")
    st.stop()

# ---------------------------------------------------------------------------
# Cart table with remove buttons
# ---------------------------------------------------------------------------
st.subheader("Items in cart")

for i, item in enumerate(cart):
    c1, c2, c3, c4, c5 = st.columns([3, 1, 1.5, 1.5, 0.8])
    c1.write(f"**{item['ProductName']}**  \n_{item.get('Size', '')}_")
    c2.write(f"Qty: {item['Qty']}")
    c3.write(f"${item['UnitPrice']:,.2f} each")
    c4.write(f"**${item['LineTotal']:,.2f}**")
    if c5.button("✕", key=f"remove_{i}"):
        cart.pop(i)
        st.rerun()

st.write("---")

total = sum(item["LineTotal"] for item in cart)
st.markdown(f"## Total: ${total:,.2f}")

col_a, col_b = st.columns(2)
with col_a:
    if st.button("Clear Cart", use_container_width=True):
        st.session_state.cart = []
        st.rerun()

with col_b:
    if st.button("✅ Submit Purchase Order", type="primary", use_container_width=True):
        orders_df = load_orders()
        po_number = generate_po_number(orders_df)
        timestamp = timestamp_now()
        user_id = cart[0].get("UserID", "GUEST")

        rows = []
        for idx, item in enumerate(cart, start=1):
            rows.append({
                "PONumber": po_number,
                "OrderID": f"{po_number}-{idx}",
                "UserID": user_id,
                "ProductID": item["ProductID"],
                "ProductName": item["ProductName"],
                "Qty": item["Qty"],
                "UnitPrice": item["UnitPrice"],
                "LineTotal": item["LineTotal"],
                "Version": 1,
                "Timestamp": timestamp,
                "Status": "Submitted",
            })

        append_order_rows(rows)
        st.session_state.cart = []
        st.success(f"Purchase Order **{po_number}** submitted successfully!")
        st.balloons()
