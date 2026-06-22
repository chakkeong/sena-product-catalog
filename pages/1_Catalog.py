import streamlit as st

from utils import load_products, load_users, get_price_for_tier, drive_thumbnail_url

st.set_page_config(page_title="Catalog — Sena Product Catalog", page_icon="📦", layout="wide")

st.title("📦 Product Catalog")

# ---------------------------------------------------------------------------
# User / tier selection (sidebar)
# ---------------------------------------------------------------------------
users_df = load_users()
products_df = load_products()

with st.sidebar:
    st.header("Buyer")
    if not users_df.empty and "Name" in users_df.columns:
        user_options = users_df["Name"].tolist() + ["Guest"]
    else:
        user_options = ["Guest"]

    selected_name = st.selectbox("Select user", user_options)

    if selected_name == "Guest":
        selected_user_id = "GUEST"
        selected_tier = "Guest"
    else:
        user_row = users_df[users_df["Name"] == selected_name].iloc[0]
        selected_user_id = user_row.get("UserID", "")
        selected_tier = user_row.get("Tier", "Guest")

    st.markdown(f"**Pricing tier:** `{selected_tier}`")

    st.write("---")
    st.header("🛒 Cart")
    cart = st.session_state.get("cart", [])
    if cart:
        cart_total = sum(item["LineTotal"] for item in cart)
        st.write(f"{len(cart)} item(s) — ${cart_total:,.2f}")
        st.page_link("pages/2_Cart.py", label="Go to Cart →", icon="🛒")
    else:
        st.write("Cart is empty")

# ---------------------------------------------------------------------------
# Search bar
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Product grid
# ---------------------------------------------------------------------------
if "cart" not in st.session_state:
    st.session_state.cart = []

NUM_COLS = 3
rows = [filtered_df.iloc[i:i + NUM_COLS] for i in range(0, len(filtered_df), NUM_COLS)]

for row_df in rows:
    cols = st.columns(NUM_COLS)
    for col, (_, product) in zip(cols, row_df.iterrows()):
        with col:
            with st.container(border=True):
                img_url = drive_thumbnail_url(product.get("ImageURL", ""))
                if img_url:
                    st.image(img_url, use_container_width=True)
                st.markdown(f"**{product.get('Name', '')}**")
                st.caption(product.get("Description", ""))
                size = product.get("Size/Measurement", "")
                if size:
                    st.markdown(
                        f"<span style='background:#EEF2FF;color:#4F46E5;padding:2px 8px;"
                        f"border-radius:10px;font-size:0.75rem;'>{size}</span>",
                        unsafe_allow_html=True,
                    )
                price = get_price_for_tier(product, selected_tier)
                st.markdown(f"### ${price:,.2f}")

                qty_key = f"qty_{product.get('ProductID')}"
                qty = st.number_input("Qty", min_value=1, value=1, step=1, key=qty_key)

                if st.button("Add to Cart", key=f"add_{product.get('ProductID')}", use_container_width=True):
                    st.session_state.cart.append({
                        "ProductID": product.get("ProductID"),
                        "ProductName": product.get("Name"),
                        "Size": size,
                        "Qty": qty,
                        "UnitPrice": price,
                        "LineTotal": price * qty,
                        "UserID": selected_user_id,
                    })
                    st.toast(f"Added {product.get('Name')} to cart", icon="🛒")
