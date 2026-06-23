import pandas as pd
import plotly.express as px
import streamlit as st

from utils import load_orders, load_products, load_users, latest_versions_only, apply_custom_css, format_currency

st.set_page_config(
    page_title="Sena Product Catalog",
    page_icon="📊",
    layout="wide",
)

apply_custom_css()

st.title("📊 Sena Product Catalog — Dashboard")
st.caption("Tiered pricing & purchase order system")

try:
    products_df = load_products()
    users_df = load_users()
    orders_df = load_orders()
except Exception as e:
    st.error(f"Could not connect to the Google Sheet. Check your secrets configuration.\n\n{e}")
    st.stop()

latest_orders = latest_versions_only(orders_df)

total_revenue = latest_orders["Total"].sum() if not latest_orders.empty else 0
total_pos = latest_orders["PO"].nunique() if not latest_orders.empty else 0
total_products = len(products_df)
total_users = len(users_df)

col1, col2, col3, col4 = st.columns(4)
for col, label, value in zip(
    [col1, col2, col3, col4],
    ["Total Revenue", "Total Purchase Orders", "Active Products", "Registered Users"],
    [f"{format_currency(total_revenue)}", f"{total_pos}", f"{total_products}", f"{total_users}"],
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

if not latest_orders.empty:
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Revenue by Tier")
        revenue_by_tier = latest_orders.groupby("Tier")["Total"].sum().reset_index().sort_values("Total", ascending=False)
        fig = px.bar(revenue_by_tier, x="Tier", y="Total", color_discrete_sequence=["#4F46E5"])
        fig.update_yaxes(tickprefix="RM ")
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
        st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.subheader("Orders Over Time")
        orders_by_date = latest_orders.copy()
        orders_by_date["Date"] = pd.to_datetime(orders_by_date["Timestamp"], errors="coerce").dt.date
        daily_counts = orders_by_date.groupby("Date")["PO"].nunique().reset_index(name="Orders")
        fig2 = px.line(daily_counts, x="Date", y="Orders", markers=True, color_discrete_sequence=["#10B981"])
        fig2.update_xaxes(type="date", tickformat="%b %d")
        fig2.update_yaxes(tick0=0, dtick=1)
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Recent Purchase Orders")
    display_orders = latest_orders.sort_values("Timestamp", ascending=False)[
        ["PO", "Email", "Tier", "Total", "Status", "Timestamp"]
    ].head(10).copy()
    display_orders["Total"] = display_orders["Total"].apply(format_currency)
    st.dataframe(display_orders, use_container_width=True, hide_index=True)
else:
    st.info("No orders yet. Head to the Catalog page to create your first purchase order.")

st.write("")
st.caption("Use the sidebar to navigate to Catalog, Cart, and Order History.")
