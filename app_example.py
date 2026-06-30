"""
app_example.py — Example of how to wire auth.py into your Sena Product Catalog
Streamlit app. Copy the relevant pieces into your existing main app file.
"""

import streamlit as st
import auth

st.set_page_config(page_title="Sena Product Catalog", layout="wide")

# Run once per session is fine to call every time; it no-ops after first migration.
auth.ensure_schema()

# ---------------------------------------------------------------------------
# Login / Signup gate
# ---------------------------------------------------------------------------

if "sena_user" not in st.session_state:
    st.title("Sena Product Catalog")
    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In")
            if submitted:
                user, error = auth.login(email, password)
                if error:
                    st.error(error)
                else:
                    st.session_state["sena_user"] = user
                    st.rerun()

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email_su = st.text_input("Email", key="signup_email")
            phone = st.text_input("Phone (optional)")
            company = st.text_input("Company (optional)")
            password_su = st.text_input("Password", type="password", key="signup_pw")
            submitted_su = st.form_submit_button("Create Account")
            if submitted_su:
                ok, msg = auth.signup(email_su, password_su, name, phone, company)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.stop()

# ---------------------------------------------------------------------------
# Logged-in app
# ---------------------------------------------------------------------------

user = st.session_state["sena_user"]

with st.sidebar:
    st.write(f"Logged in as **{user['Name']}**")
    st.write(f"Role: {user['Role']} | Tier: {user['Tier']}")
    if st.button("Log Out"):
        auth.logout()
        st.rerun()

if auth.is_admin(user):
    tab_catalog, tab_orders, tab_users, tab_products = st.tabs(
        ["Catalog", "Orders", "User Management", "Product Management"]
    )
else:
    (tab_catalog,) = st.tabs(["Catalog"])

with tab_catalog:
    st.header("Product Catalog")
    price_col = auth.get_price_column(user)
    st.caption(f"Showing prices from: {price_col}")
    # TODO: load Products sheet, render catalog using price_col for this user

if auth.is_admin(user):
    with tab_orders:
        st.header("All Orders")
        # TODO: load Orders sheet, show all rows (no filtering by user)

    with tab_users:
        st.header("User Management")

        st.subheader("Pending Approvals")
        pending = auth.list_pending_users()
        if pending.empty:
            st.info("No pending users.")
        else:
            for idx, row in pending.iterrows():
                cols = st.columns([3, 2, 2, 2])
                cols[0].write(row["Email"])
                tier_choice = cols[1].selectbox(
                    "Assign Tier",
                    ["Consumer", "Tier1", "Tier2", "Tier3"],
                    key=f"tier_{idx}",
                )
                if cols[2].button("Approve", key=f"approve_{idx}"):
                    auth.update_user(row["Email"], Status="active", Tier=tier_choice)
                    st.rerun()
                if cols[3].button("Reject", key=f"reject_{idx}"):
                    auth.update_user(row["Email"], Status="disabled")
                    st.rerun()

        st.subheader("All Users")
        df = auth.load_users_df()
        st.dataframe(df.drop(columns=["Password"]), use_container_width=True)
        # TODO: add edit/disable/delete controls per row using auth.update_user / auth.delete_user

    with tab_products:
        st.header("Product Management")
        # TODO: load Products sheet, add add/edit/delete forms
