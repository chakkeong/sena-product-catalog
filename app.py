import pandas as pd
import plotly.express as px
import streamlit as st

from utils import load_orders, load_products, load_users, latest_versions_only

st.set_page_config(
    page_title="Sena Product Catalog",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom styling for a cleaner, more professional look
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .kpi-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        border: 1px solid #eaeaea;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #6b7280;
        font-weight: 500;
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #111827;
    }
    section[data-testid="stSidebar"] {
        border-right: 1px solid #eaeaea;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Sena Product Catalog — Dashboard")
st.caption("Tiered pricing & purchase order system")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
try:
    products_df = load_products()
    users_df = load_users()
    orders_df = load_orders()
except Exception as e:
    st.error(f"Could not connect to the Google Sheet. Check your secrets configuration.\n\n{e}")
    st.stop()

latest_orders = latest_versions_only(orders_df)

total_revenue = latest_orders["LineTotal"].sum() if not latest_orders.empty else 0
total_pos = latest_orders["PONumber"].nunique() if not latest_orders.empty else 0
total_products = len(products_df)
total_users = len(users_df)

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
for col, label, value in zip(
    [col1, col2, col3, col4],
    ["Total Revenue", "Total Purchase Orders", "Active Products", "Registered Users"],
    [f"${total_revenue:,.2f}", f"{total_pos}", f"{total_products}", f"{total_users}"],
):
    with col:
        st.markdown(
            f"""<div class="kpi-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                </div>""",
            unsafe_allow_html=True,
        )

st.write("")

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
if not latest_orders.empty:
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Revenue by User")
        revenue_by_user = (
            latest_orders.groupby("UserID")["LineTotal"].sum().reset_index().sort_values("LineTotal", ascending=False)
        )
        fig = px.bar(
            revenue_by_user, x="UserID", y="LineTotal",
            color_discrete_sequence=["#4F46E5"],
        )
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
        st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.subheader("Orders Over Time")
        orders_by_date = latest_orders.copy()
        orders_by_date["Date"] = pd.to_datetime(orders_by_date["Timestamp"], errors="coerce").dt.date
        daily_counts = orders_by_date.groupby("Date")["PONumber"].nunique().reset_index(name="Orders")
        fig2 = px.line(
            daily_counts, x="Date", y="Orders", markers=True,
            color_discrete_sequence=["#10B981"],
        )
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Recent Purchase Orders")
    st.dataframe(
        latest_orders.sort_values("Timestamp", ascending=False)[
            ["PONumber", "UserID", "ProductName", "Qty", "LineTotal", "Status", "Timestamp"]
        ].head(10),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No orders yet. Head to the Catalog page to create your first purchase order.")

st.write("")
st.caption("Use the sidebar to navigate to Catalog, Cart, and Order History.")
