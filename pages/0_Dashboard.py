import pandas as pd
import plotly.express as px
import streamlit as st

from utils import (
    load_orders,
    load_products,
    load_users,
    latest_versions_only,
    apply_custom_css,
    format_currency,
    render_brand_header,
    render_contact_widget,
    gate_access,
    is_admin,
    render_top_navbar,
    LOGO_PATH,
    get_pending_applications,
    approve_application,
    reject_application,
    APPROVABLE_TIERS,
    load_showcase_content,
    save_showcase_value,
    upload_image_to_drive,
)

st.set_page_config(
    page_title="Sena Product Catalog",
    page_icon=LOGO_PATH,
    layout="wide",
)

apply_custom_css()
render_contact_widget()
user_record = gate_access()
render_top_navbar(user_record, st.session_state.get("nav_pages", []))

if not is_admin(user_record):
    st.warning("🔒 This dashboard is restricted to administrators. Use the sidebar to go to Catalog instead.")
    st.stop()

render_brand_header("Sena Product Catalog — Dashboard", "Tiered pricing & purchase order system")

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

# ---------------------------------------------------------------------------
# Pending Access Requests — admin approves and assigns a tier right here
# ---------------------------------------------------------------------------

st.subheader("🔑 Pending Access Requests")

try:
    pending_df = get_pending_applications()
except Exception as e:
    pending_df = pd.DataFrame()
    st.error(f"Could not load applications: {e}")

if pending_df.empty:
    st.info("No pending access requests right now.")
else:
    for _, row in pending_df.iterrows():
        applicant_email = row.get("Email", "")
        applicant_timestamp = row.get("Timestamp", "")
        row_key = f"{applicant_email}_{applicant_timestamp}"

        with st.container(border=True):
            info_col, tier_col, approve_col, reject_col = st.columns([3, 1.4, 1, 1])

            with info_col:
                st.markdown(f"**{row.get('Name', '')}** — {applicant_email}")
                st.caption(f"{row.get('Company', '')} · {row.get('Phone', '')} · Requested {applicant_timestamp}")

            with tier_col:
                tier_choice = st.selectbox(
                    "Tier",
                    APPROVABLE_TIERS,
                    key=f"tier_{row_key}",
                    label_visibility="collapsed",
                )

            with approve_col:
                if st.button("✅ Approve", key=f"approve_{row_key}", width="stretch"):
                    approve_application(applicant_email, tier_choice)
                    st.success(f"Approved {applicant_email} as {tier_choice}")
                    st.rerun()

            with reject_col:
                if st.button("❌ Reject", key=f"reject_{row_key}", width="stretch"):
                    reject_application(applicant_email)
                    st.warning(f"Rejected {applicant_email}")
                    st.rerun()

st.write("")

if not latest_orders.empty:
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Revenue by Tier")
        revenue_by_tier = latest_orders.groupby("Tier")["Total"].sum().reset_index().sort_values("Total", ascending=False)
        fig = px.bar(revenue_by_tier, x="Tier", y="Total", color_discrete_sequence=["#C9A227"])
        fig.update_yaxes(tickprefix="RM ")
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
        st.plotly_chart(fig, width="stretch")

    with chart_col2:
        st.subheader("Orders Over Time")
        orders_by_date = latest_orders.copy()
        orders_by_date["Date"] = pd.to_datetime(orders_by_date["Timestamp"], errors="coerce").dt.date
        daily_counts = orders_by_date.groupby("Date")["PO"].nunique().reset_index(name="Orders")
        fig2 = px.line(daily_counts, x="Date", y="Orders", markers=True, color_discrete_sequence=["#10B981"])
        fig2.update_xaxes(type="date", tickformat="%b %d")
        fig2.update_yaxes(tick0=0, dtick=1)
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
        st.plotly_chart(fig2, width="stretch")

    st.subheader("Recent Purchase Orders")
    display_orders = latest_orders.sort_values("Timestamp", ascending=False)[
        ["PO", "Email", "Tier", "Total", "Status", "Timestamp"]
    ].head(10).copy()
    display_orders["Total"] = display_orders["Total"].apply(format_currency)
    st.dataframe(display_orders, width="stretch", hide_index=True)
else:
    st.info("No orders yet. Head to the Catalog page to create your first purchase order.")

st.write("")

# ---------------------------------------------------------------------------
# Showcase Page Editor — change the public Showcase page's photos and
# writing directly, no code edits or spreadsheet wrangling required.
# ---------------------------------------------------------------------------

st.subheader("🖼️ Showcase Page Editor")
st.caption("Edit what visitors see on your public Showcase page. Changes go live as soon as you save.")

try:
    showcase_content = load_showcase_content()
except Exception as e:
    showcase_content = {}
    st.error(f"Could not load Showcase content: {e}")

with st.expander("Top headline & intro text"):
    with st.form("showcase_hero_form"):
        hero_eyebrow = st.text_input(
            "Small label above the headline",
            value=showcase_content.get("hero_eyebrow", ""),
        )
        hero_headline = st.text_area(
            "Headline",
            value=showcase_content.get("hero_headline", ""),
            height=80,
        )
        hero_lead = st.text_area(
            "Intro paragraph",
            value=showcase_content.get("hero_lead", ""),
            height=100,
        )
        if st.form_submit_button("Save headline & intro"):
            save_showcase_value("hero_eyebrow", hero_eyebrow)
            save_showcase_value("hero_headline", hero_headline)
            save_showcase_value("hero_lead", hero_lead)
            st.success("Headline and intro updated.")
            st.rerun()

CONCEPT_TABS = [("homey", "Homey"), ("insta", "Insta"), ("modern", "Modern")]
concept_tabs = st.tabs([label for _, label in CONCEPT_TABS])

for tab, (concept_id, concept_label) in zip(concept_tabs, CONCEPT_TABS):
    with tab:
        photo_col, fields_col = st.columns([1, 2])

        current_image = showcase_content.get(f"{concept_id}_hero_image", "")
        with photo_col:
            if current_image:
                st.image(current_image, width="stretch", caption="Current photo")
            else:
                st.caption("No photo set yet.")

        with fields_col:
            with st.form(f"showcase_form_{concept_id}"):
                new_label = st.text_input(
                    "Concept name",
                    value=showcase_content.get(f"{concept_id}_label", concept_label),
                    key=f"label_{concept_id}",
                )
                new_mood = st.text_area(
                    "Mood / description",
                    value=showcase_content.get(f"{concept_id}_mood", ""),
                    height=130,
                    key=f"mood_{concept_id}",
                )
                new_photo = st.file_uploader(
                    "Replace photo (optional)",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"upload_{concept_id}",
                )
                if st.form_submit_button(f"Save {concept_label}"):
                    save_showcase_value(f"{concept_id}_label", new_label)
                    save_showcase_value(f"{concept_id}_mood", new_mood)
                    if new_photo is not None:
                        with st.spinner("Uploading photo to Drive..."):
                            try:
                                new_url = upload_image_to_drive(
                                    new_photo.getvalue(),
                                    new_photo.name,
                                    new_photo.type or "image/jpeg",
                                )
                                save_showcase_value(f"{concept_id}_hero_image", new_url)
                            except Exception as e:
                                st.error(f"Photo upload failed: {e}")
                                st.stop()
                    st.success(f"{concept_label} updated.")
                    st.rerun()

st.write("")
st.caption("Use the sidebar to navigate to Catalog, Cart, and Order History.")
