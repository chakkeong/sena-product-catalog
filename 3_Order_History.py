import streamlit as st

from utils import (
    load_orders,
    latest_versions_only,
    get_next_version,
    append_order_rows,
    timestamp_now,
)

st.set_page_config(page_title="Order History — Sena Product Catalog", page_icon="📋", layout="wide")

st.title("📋 Purchase Order History")

orders_df = load_orders()

if orders_df.empty:
    st.info("No purchase orders yet.")
    st.stop()

latest = latest_versions_only(orders_df)
po_list = sorted(latest["PONumber"].unique(), reverse=True)

search = st.text_input("🔍 Search by PO number or User ID")
if search:
    po_list = [po for po in po_list if search.lower() in po.lower()]

st.caption(f"{len(po_list)} purchase order(s)")

for po_number in po_list:
    po_lines = orders_df[orders_df["PONumber"] == po_number]
    current_version = int(po_lines["Version"].max())
    current_lines = po_lines[po_lines["Version"] == current_version]
    po_total = current_lines["LineTotal"].sum()
    user_id = current_lines["UserID"].iloc[0] if not current_lines.empty else ""
    status = current_lines["Status"].iloc[0] if not current_lines.empty else ""

    with st.expander(f"**{po_number}** — {user_id} — ${po_total:,.2f} — v{current_version} — {status}"):
        st.dataframe(
            current_lines[["ProductName", "Qty", "UnitPrice", "LineTotal"]],
            use_container_width=True,
            hide_index=True,
        )

        if current_version > 1:
            with st.popover("View full version history"):
                st.dataframe(
                    po_lines.sort_values(["Version"])[
                        ["Version", "ProductName", "Qty", "UnitPrice", "LineTotal", "Timestamp", "Status"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

        st.write("---")
        st.markdown("**Amend this order**")
        st.caption("Editing quantities and saving creates a new version — the original is preserved in history.")

        edited_rows = []
        for _, line in current_lines.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(line["ProductName"])
            new_qty = c2.number_input(
                "Qty", min_value=0, value=int(line["Qty"]), step=1,
                key=f"amend_qty_{po_number}_{line['ProductID']}", label_visibility="collapsed",
            )
            c3.write(f"${float(line['UnitPrice']) * new_qty:,.2f}")
            edited_rows.append({
                "ProductID": line["ProductID"],
                "ProductName": line["ProductName"],
                "UnitPrice": float(line["UnitPrice"]),
                "Qty": new_qty,
            })

        if st.button("💾 Save Amendment", key=f"save_{po_number}"):
            next_version = get_next_version(orders_df, po_number)
            timestamp = timestamp_now()
            new_rows = []
            for idx, row in enumerate(edited_rows, start=1):
                if row["Qty"] <= 0:
                    continue
                new_rows.append({
                    "PONumber": po_number,
                    "OrderID": f"{po_number}-v{next_version}-{idx}",
                    "UserID": user_id,
                    "ProductID": row["ProductID"],
                    "ProductName": row["ProductName"],
                    "Qty": row["Qty"],
                    "UnitPrice": row["UnitPrice"],
                    "LineTotal": row["UnitPrice"] * row["Qty"],
                    "Version": next_version,
                    "Timestamp": timestamp,
                    "Status": "Amended",
                })
            if new_rows:
                append_order_rows(new_rows)
                st.success(f"{po_number} updated to version {next_version}")
                st.rerun()
            else:
                st.warning("All quantities are zero — nothing to save.")
