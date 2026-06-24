"""
Shared utilities for Sena Product Catalog.
Matches the EXISTING sheet structure:
  Users:    Email, Tier
  Products: ProductID, Name, Description, Tier1Price, Tier2Price, Tier3Price,
            ConsumerPrice, ImageURL, Size/Measurement
  Orders:   PO, Timestamp, Email, Tier, ItemsJSON, Total, Status, Version
            (one row per PO/version; ItemsJSON is a JSON string of line items)
"""

import json
import re
import time
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TIER_PRICE_COLUMN = {
    "Tier1": "Tier1Price",
    "Tier2": "Tier2Price",
    "Tier3": "Tier3Price",
    "Consumer": "ConsumerPrice",
    "Guest": "ConsumerPrice",
}

ORDERS_COLUMNS = ["PO", "Timestamp", "Email", "Tier", "ItemsJSON", "Total", "Status", "Version"]
APPLICATIONS_COLUMNS = ["Timestamp", "Name", "Email", "Phone", "Company", "Status"]


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_spreadsheet():
    client = get_client()
    return client.open_by_key(st.secrets["sheet_id"])


# ---------------------------------------------------------------------------
# Loading data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def load_sheet(tab_name: str) -> pd.DataFrame:
    ws = get_spreadsheet().worksheet(tab_name)
    records = ws.get_all_records()
    return pd.DataFrame(records)


def load_products() -> pd.DataFrame:
    df = load_sheet("Products")
    for col in ["Tier1Price", "Tier2Price", "Tier3Price", "ConsumerPrice"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def load_users() -> pd.DataFrame:
    return load_sheet("Users")


def load_orders() -> pd.DataFrame:
    df = load_sheet("Orders")
    if df.empty:
        return pd.DataFrame(columns=ORDERS_COLUMNS)
    if "Total" in df.columns:
        df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
    if "Version" in df.columns:
        df["Version"] = pd.to_numeric(df["Version"], errors="coerce").fillna(1).astype(int)
        df.loc[df["Version"] < 1, "Version"] = 1
    else:
        df["Version"] = 1
    return df


def clear_cache():
    load_sheet.clear()


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

def get_price_for_tier(product_row: pd.Series, tier: str) -> float:
    col = TIER_PRICE_COLUMN.get(tier, "ConsumerPrice")
    return float(product_row.get(col, 0) or 0)


def drive_thumbnail_url(image_url: str) -> str:
    if not image_url:
        return ""
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", image_url) or re.search(r"id=([a-zA-Z0-9_-]+)", image_url)
    if match:
        return f"https://drive.google.com/thumbnail?id={match.group(1)}&sz=w1200"
    return image_url


# ---------------------------------------------------------------------------
# Items JSON helpers
# ---------------------------------------------------------------------------

def parse_items(items_json: str) -> list[dict]:
    """Parse the ItemsJSON column into a list of line-item dicts."""
    if not items_json:
        return []
    try:
        return json.loads(items_json)
    except (json.JSONDecodeError, TypeError):
        return []


def items_total(items: list[dict]) -> float:
    return sum(float(i.get("price", 0)) * float(i.get("qty", 0)) for i in items)


# ---------------------------------------------------------------------------
# PO numbering / versioning
# ---------------------------------------------------------------------------

def generate_po_number() -> str:
    """Generate a PO number using a timestamp, matching the existing scheme."""
    return f"PO-{int(time.time())}"


def get_next_version(orders_df: pd.DataFrame, po_number: str) -> int:
    if orders_df.empty:
        return 1
    existing = orders_df[orders_df["PO"] == po_number]
    if existing.empty:
        return 1
    return int(existing["Version"].max()) + 1


def latest_versions_only(orders_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse the orders table down to only the latest version of each PO."""
    if orders_df.empty:
        return orders_df
    idx = orders_df.groupby("PO")["Version"].idxmax()
    return orders_df.loc[idx].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Writing data
# ---------------------------------------------------------------------------

def append_row_generic(tab_name: str, row: dict, expected_columns: list[str]):
    """Append one row to any tab. Creates the header row if the tab is empty."""
    ws = get_spreadsheet().worksheet(tab_name)
    existing_headers = ws.row_values(1)
    if not existing_headers:
        ws.append_row(expected_columns)
        existing_headers = expected_columns
    ordered_row = [row.get(col, "") for col in existing_headers]
    ws.append_row(ordered_row, value_input_option="USER_ENTERED")
    clear_cache()


def append_order_row(row: dict):
    """Append one new PO/version row. Never overwrites existing history."""
    append_row_generic("Orders", row, ORDERS_COLUMNS)


LOGO_PATH = "Assets/logo.png"
FACEBOOK_URL = "https://www.facebook.com/profile.php?id=61589913425326"
WHATSAPP_URL = "https://wa.me/60136338923"


def render_contact_widget():
    """Render a floating Facebook + WhatsApp contact widget in the corner of the page."""
    st.markdown(
        f"""
        <div class="contact-widget">
            <a href="{FACEBOOK_URL}" target="_blank" class="contact-btn contact-fb">f</a>
            <a href="{WHATSAPP_URL}" target="_blank" class="contact-btn contact-wa">💬</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_brand_header(title: str, subtitle: str = ""):
    """Render a consistent branded header with the company logo, title, and subtitle."""
    logo_col, title_col = st.columns([1, 6], vertical_alignment="center")
    with logo_col:
        st.image(LOGO_PATH, use_container_width=True)
    with title_col:
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)
    st.write("")


def render_sidebar_logo():
    """Render a small logo at the top of the sidebar for consistent branding."""
    with st.sidebar:
        st.image(LOGO_PATH, use_container_width=True)
        st.write("---")


def format_currency(value) -> str:
    """Format a number as Malaysian Ringgit, e.g. RM 1,234.50"""
    try:
        return f"RM {float(value):,.2f}"
    except (TypeError, ValueError):
        return f"RM {value}"


def timestamp_now() -> str:
    return datetime.now().strftime("%-m/%-d/%Y %H:%M")


# ---------------------------------------------------------------------------
# Login & access control
# ---------------------------------------------------------------------------

def is_admin(user_record: dict) -> bool:
    """Check the Users tab 'Role' column to see if this person is an admin."""
    role = str(user_record.get("Role", "")).strip().lower()
    return role == "admin"


def get_user_record(email: str):
    """Look up an approved user by email in the Users tab. Returns a dict or None."""
    users_df = load_users()
    if users_df.empty or "Email" not in users_df.columns or not email:
        return None
    matches = users_df[users_df["Email"].astype(str).str.strip().str.lower() == email.strip().lower()]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def submit_application(name: str, email: str, phone: str, company: str):
    row = {
        "Timestamp": timestamp_now(),
        "Name": name,
        "Email": email,
        "Phone": phone,
        "Company": company,
        "Status": "Pending",
    }
    append_row_generic("Applications", row, APPLICATIONS_COLUMNS)


def get_latest_application(email: str):
    """Return the most recent application row for this email, or None."""
    try:
        df = load_sheet("Applications")
    except Exception:
        return None
    if df.empty or "Email" not in df.columns or not email:
        return None
    matches = df[df["Email"].astype(str).str.strip().str.lower() == email.strip().lower()]
    if matches.empty:
        return None
    return matches.iloc[-1].to_dict()


def render_login_screen():
    st.markdown("## 🔒 Sena Product Catalog")
    st.write("Please log in with your Google account to continue.")
    if st.button("Log in with Google", type="primary"):
        st.login()

    st.write("")
    st.caption("Just browsing? No account needed for guest pricing.")
    if st.button("Continue as Guest"):
        st.session_state["guest_mode"] = True
        st.rerun()


def render_pending_or_apply(email: str):
    application = get_latest_application(email)
    status = str(application.get("Status", "")).strip().lower() if application else ""

    if st.button("← Log out / use a different email"):
        st.session_state.pop("guest_mode", None)
        st.logout()

    if status == "pending":
        st.info(f"Your access request for **{email}** is pending review. You'll get access once approved.")
        st.stop()

    if status == "rejected":
        st.warning("Your previous access request was not approved. Please contact us if you believe this is a mistake.")
        st.stop()

    st.subheader("Request Access")
    st.caption(f"Signed in as **{email}**. You don't have catalog access yet — submit a request below.")
    with st.form("access_request_form"):
        name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")
        company = st.text_input("Company")
        submitted = st.form_submit_button("Submit Request")

    if submitted:
        if not name or not phone or not company:
            st.warning("Please fill in all fields.")
        else:
            submit_application(name, email, phone, company)
            st.success("Your request has been submitted! You'll get access once approved.")
            st.rerun()

    st.stop()


GUEST_RECORD = {"Email": "guest@guest.local", "Name": "Guest", "Tier": "Guest"}


def gate_access() -> dict:
    """
    Require Google login and Users-tab approval before showing any page content,
    unless the visitor has chosen to continue as a Guest.
    Returns a user record (dict) if successful; otherwise stops the page.
    """
    if st.session_state.get("guest_mode"):
        return GUEST_RECORD

    if not st.user.is_logged_in:
        render_login_screen()
        st.stop()

    email = st.user.email
    user_record = get_user_record(email)
    if user_record:
        return user_record

    render_pending_or_apply(email)


def render_user_sidebar(user_record: dict):
    with st.sidebar:
        st.write(f"👤 **{user_record.get('Name') or user_record.get('Email', '')}**")
        st.markdown(f'<span class="tier-badge">{user_record.get("Tier", "")}</span>', unsafe_allow_html=True)
        if st.session_state.get("guest_mode"):
            if st.button("Exit Guest Mode", use_container_width=True):
                st.session_state.pop("guest_mode", None)
                st.rerun()
        else:
            if st.button("Log out", use_container_width=True):
                st.logout()
        st.write("---")


# ---------------------------------------------------------------------------
# Shared visual styling
# ---------------------------------------------------------------------------

def apply_custom_css():
    """Inject shared CSS for a consistent, polished look across all pages."""
    st.markdown(
        """
        <style>
        :root, html, body, .stApp {
            color-scheme: light only;
            forced-color-adjust: none;
        }
        .stApp { background-color: #FAFAFB; }

        h1, h2, h3 { color: #111827; font-weight: 700; }

        .kpi-card {
            background: #ffffff;
            border-radius: 16px;
            padding: 1.3rem 1.5rem;
            border: 1px solid #ECECEF;
            box-shadow: 0 2px 12px rgba(17,24,39,0.05);
        }
        .kpi-label { font-size: 0.82rem; color: #6B7280; font-weight: 600; letter-spacing: 0.02em; text-transform: uppercase; margin-bottom: 0.35rem; }
        .kpi-value { font-size: 1.9rem; font-weight: 800; color: #111827; }

        .product-card {
            background: #ffffff;
            border-radius: 18px;
            border: 1px solid #ECECEF;
            box-shadow: 0 2px 10px rgba(17,24,39,0.04);
            overflow: hidden;
            transition: box-shadow 0.15s ease;
        }
        .product-image-wrap {
            width: 100%;
            height: 200px;
            overflow: hidden;
            border-radius: 14px;
            background: #F3F4F6;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .product-image-wrap img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .price-tag {
            font-size: 1.5rem;
            font-weight: 800;
            color: #4F46E5;
            margin-top: 10px;
        }
        .price-row {
            display: flex;
            flex-direction: column;
            gap: 2px;
            margin-top: 10px;
        }
        .price-your-label {
            font-size: 0.7rem;
            font-weight: 700;
            color: #059669;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .price-retail-label {
            font-size: 0.7rem;
            font-weight: 600;
            color: #9CA3AF;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-top: 6px;
        }
        .price-strike {
            font-size: 0.95rem;
            font-weight: 600;
            color: #9CA3AF;
            text-decoration: line-through;
        }
        .size-badge-row {
            min-height: 26px;
            margin-bottom: 8px;
            display: block;
        }
        .size-badge {
            background: #EEF2FF;
            color: #4F46E5;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.72rem;
            font-weight: 600;
            display: inline-block;
        }
        .tier-badge {
            background: #ECFDF5;
            color: #059669;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-block;
        }

        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #ECECEF;
        }

        div[data-testid="stButton"] button {
            border-radius: 10px;
            font-weight: 600;
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background-color: #4F46E5;
            border-color: #4F46E5;
        }

        [data-testid="stExpander"] {
            border-radius: 14px;
            border: 1px solid #ECECEF;
        }

        .contact-widget {
            position: fixed;
            bottom: 24px;
            right: 24px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            z-index: 9999;
        }
        .contact-btn {
            width: 52px;
            height: 52px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white !important;
            font-weight: 800;
            font-size: 1.5rem;
            text-decoration: none !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.25);
        }
        .contact-fb { background: #1877F2; font-family: Georgia, serif; }
        .contact-wa { background: #25D366; }
        </style>
        """,
        unsafe_allow_html=True,
    )
