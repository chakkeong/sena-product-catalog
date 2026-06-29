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
    load_concepts,
    add_concept,
    update_concept,
    delete_concept,
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

try:
    concepts = load_concepts()
except Exception as e:
    concepts = []
    st.error(f"Could not load concepts: {e}")

if not concepts:
    st.info("No concepts yet — add your first one below.")
else:
    concept_ids = [c["id"] for c in concepts]
    concept_labels = [c["label"] or c["id"].title() for c in concepts]

    # Tabs reset to the first one on every rerun (e.g. right after saving),
    # which made successful saves on other concepts look like nothing
    # happened. A radio tied to session_state remembers the selection instead.
    if st.session_state.get("dashboard_active_concept") not in concept_ids:
        st.session_state["dashboard_active_concept"] = concept_ids[0]

    selected_label = st.radio(
        "Concept",
        concept_labels,
        index=concept_ids.index(st.session_state["dashboard_active_concept"]),
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_id = concept_ids[concept_labels.index(selected_label)]
    st.session_state["dashboard_active_concept"] = selected_id
    cdef = next(c for c in concepts if c["id"] == selected_id)

    photo_col, fields_col = st.columns([1, 2])

    with photo_col:
        if cdef["hero_image"]:
            st.image(cdef["hero_image"], width="stretch", caption="Current photo")
        else:
            st.caption("No photo set yet.")

    with fields_col:
        with st.form(f"showcase_form_{selected_id}"):
            new_label = st.text_input("Concept name", value=cdef["label"], key=f"label_{selected_id}")
            new_keyword = st.text_input(
                "Match keyword",
                value=cdef["keyword"],
                key=f"keyword_{selected_id}",
                help=(
                    "Products whose Name contains this word (e.g. \"homey\") are shown under "
                    "this concept. Must match something in your Products sheet."
                ),
            )
            new_mood = st.text_area(
                "Mood / description",
                value=cdef["mood"],
                height=130,
                key=f"mood_{selected_id}",
            )
            new_photo = st.file_uploader(
                "Replace photo (optional)",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"upload_{selected_id}",
            )
            if new_photo is not None:
                st.image(new_photo, width="stretch", caption="New photo — not saved yet")

            save_col, delete_col = st.columns([3, 1])
            with save_col:
                saved = st.form_submit_button("Save changes", width="stretch")
            with delete_col:
                deleted = st.form_submit_button("🗑️ Delete", width="stretch")

            if saved:
                updates = {"Label": new_label, "Keyword": new_keyword, "Mood": new_mood}
                if new_photo is not None:
                    with st.spinner("Uploading photo to Drive..."):
                        try:
                            updates["HeroImageURL"] = upload_image_to_drive(
                                new_photo.getvalue(),
                                new_photo.name,
                                new_photo.type or "image/jpeg",
                            )
                        except Exception as e:
                            st.error(f"Photo upload failed: {e}")
                            st.stop()
                update_concept(selected_id, updates)
                st.success(f"{new_label or selected_id} updated.")
                st.rerun()

            if deleted:
                delete_concept(selected_id)
                st.success(f"{cdef['label'] or selected_id} removed.")
                st.rerun()

with st.expander("➕ Add a new concept"):
    with st.form("add_concept_form", clear_on_submit=True):
        add_label = st.text_input("Concept name", placeholder="e.g. Scandi")
        add_keyword = st.text_input(
            "Match keyword",
            placeholder="e.g. scandi",
            help=(
                "Products whose Name contains this word will show up under this concept. "
                "Make sure some of your Products sheet rows actually include it."
            ),
        )
        add_mood = st.text_area("Mood / description", height=100)
        add_photo = st.file_uploader("Photo", type=["jpg", "jpeg", "png", "webp"])
        if add_photo is not None:
            st.image(add_photo, width="stretch", caption="Photo preview — not saved yet")
        if st.form_submit_button("Add concept"):
            if not add_label or not add_keyword:
                st.warning("Please give the concept a name and a match keyword.")
            else:
                hero_url = ""
                if add_photo is not None:
                    with st.spinner("Uploading photo to Drive..."):
                        try:
                            hero_url = upload_image_to_drive(
                                add_photo.getvalue(),
                                add_photo.name,
                                add_photo.type or "image/jpeg",
                            )
                        except Exception as e:
                            st.error(f"Photo upload failed: {e}")
                            st.stop()
                add_concept(add_label, add_keyword, add_mood, hero_url)
                st.success(f"{add_label} added.")
                st.rerun()

st.write("")
st.caption("Use the sidebar to navigate to Catalog, Cart, and Order History.")
