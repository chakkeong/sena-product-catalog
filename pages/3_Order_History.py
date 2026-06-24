import json

import pandas as pd
import streamlit as st

from utils import (
    load_orders,
    latest_versions_only,
    get_next_version,
    append_order_row,
    timestamp_now,
    parse_items,
    apply_custom_css,
    format_currency,
    render_brand_header,
    render_sidebar_logo,
    render_user_sidebar,
    render_contact_widget,
    gate_access,
    is_admin,
    get_user_record,
    LOGO_PATH,
)
from pdf_generator import generate_po_pdf

st.set_page_config(page_title="Order History — Sena Product Catalog", page_icon=LOGO_PATH, layout="wide")
apply_custom_css()
render_sidebar_logo()
render_contact_widget()
user_record = gate_access()
render_user_sidebar(user_record)
render_brand_header("Purchase Order History")

orders_df = load_orders()

if orders_df.empty:
    st.info("No purchase orders yet.")
    st.stop()

# ---------------------------------------------------------------------------
# Admins see every order; everyone else only sees their own.
# ---------------------------------------------------------------------------
viewer_is_admin = is_admin(user_record)
viewer_email = str(user_record.get("Email", "")).strip().lower()

if not viewer_is_admin:
    orders_df = orders_df[orders_df["Email"].astype(str).str.strip().str.lower() == viewer_email]
    if orders_df.empty:
        st.info("You haven't placed any purchase orders yet.")
        st.stop()

latest = latest_versions_only(orders_df)
po_list = sorted(latest["PO"].unique(), reverse=True)

search = st.text_input("🔍 Search by PO number or email") if viewer_is_admin else st.text_input("🔍 Search by PO number")
if search:
    po_list = [po for po in po_list if search.lower() in po.lower()]

st.caption(f"{len(po_list)} purchase order(s)")

for po_number in po_list:
    po_versions = orders_df[orders_df["PO"] == po_number]
    current_version_num = int(po_versions["Version"].max())
    current_row = po_versions[po_versions["Version"] == current_version_num].iloc[0]
    items = parse_items(current_row.get("ItemsJSON", ""))
    email = current_row.get("Email", "")
    status = current_row.get("Status", "")
    total = current_row.get("Total", 0)

    expander_label = (
        f"**{po_number}** — {email} — {format_currency(total)} — v{current_version_num} — {status}"
        if viewer_is_admin
        else f"**{po_number}** — {format_currency(total)} — v{current_version_num} — {status}"
    )

    with st.expander(expander_label):
        items_df = pd.DataFrame(items)
        if not items_df.empty:
            display_df = items_df.rename(columns={"name": "Product", "qty": "Qty", "price": "Unit Price", "size": "Size"})
            display_df["Line Total"] = display_df["Qty"] * display_df["Unit Price"]
            display_df["Unit Price"] = display_df["Unit Price"].apply(format_currency)
            display_df["Line Total"] = display_df["Line Total"].apply(format_currency)
            st.dataframe(
                display_df[["Product", "Size", "Qty", "Unit Price", "Line Total"]],
                use_container_width=True, hide_index=True,
            )

        customer_record = get_user_record(email) or {}
        pdf_bytes = generate_po_pdf(
            po_number=po_number,
            customer_name=customer_record.get("Name", "") or email,
            customer_email=email,
            customer_company=customer_record.get("Company", ""),
            customer_phone=customer_record.get("Phone", ""),
            tier=current_row.get("Tier", ""),
            status=status,
            timestamp=current_row.get("Timestamp", ""),
            items=items,
            total=total,
            version=current_version_num,
        )
        st.download_button(
            "📄 Download PDF",
            data=pdf_bytes,
            file_name=f"{po_number}.pdf",
            mime="application/pdf",
            key=f"pdf_{po_number}",
        )

        if current_version_num > 1:
            with st.popover("View full version history"):
                for _, vrow in po_versions.sort_values("Version").iterrows():
                    v_items = parse_items(vrow.get("ItemsJSON", ""))
                    st.markdown(f"**Version {int(vrow['Version'])}** — {vrow.get('Timestamp', '')} — {vrow.get('Status', '')} — {format_currency(vrow.get('Total', 0))}")
                    for it in v_items:
                        st.write(f"  • {it.get('name')} × {it.get('qty')} @ {format_currency(it.get('price'))}")

        st.write("---")
        st.markdown("**Amend this order**")
        st.caption("Editing quantities and saving creates a new version — the original is preserved in history.")

        edited_items = []
        for idx, it in enumerate(items):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(it.get("name", ""))
            new_qty = c2.number_input(
                "Qty", min_value=0, value=int(it.get("qty", 0)), step=1,
                key=f"amend_qty_{po_number}_{idx}", label_visibility="collapsed",
            )
            c3.write(format_currency(float(it.get("price", 0)) * new_qty))
            edited_items.append({
                "id": it.get("id"), "name": it.get("name"),
                "price": float(it.get("price", 0)), "qty": new_qty, "size": it.get("size", ""),
            })

        if st.button("💾 Save Amendment", key=f"save_{po_number}"):
            kept_items = [i for i in edited_items if i["qty"] > 0]
            if not kept_items:
                st.warning("All quantities are zero — nothing to save.")
            else:
                next_version = get_next_version(orders_df, po_number)
                new_total = sum(i["price"] * i["qty"] for i in kept_items)
                row = {
                    "PO": po_number,
                    "Timestamp": timestamp_now(),
                    "Email": email,
                    "Tier": current_row.get("Tier", ""),
                    "ItemsJSON": json.dumps(kept_items),
                    "Total": new_total,
                    "Status": "Amended",
                    "Version": next_version,
                }
                append_order_row(row)
                st.success(f"{po_number} updated to version {next_version}")
                st.rerun()
