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

def append_order_row(row: dict):
    """Append one new PO/version row. Never overwrites existing history."""
    ws = get_spreadsheet().worksheet("Orders")
    existing_headers = ws.row_values(1)
    if not existing_headers:
        ws.append_row(ORDERS_COLUMNS)
        existing_headers = ORDERS_COLUMNS
    ordered_row = [row.get(col, "") for col in existing_headers]
    ws.append_row(ordered_row, value_input_option="USER_ENTERED")
    clear_cache()


LOGO_PATH = "assets/logo.png"


def render_brand_header(title: str, subtitle: str = ""):
    """Render a consistent branded header with the company logo, title, and subtitle."""
    logo_col, title_col = st.columns([1, 6])
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
# Shared visual styling
# ---------------------------------------------------------------------------

def apply_custom_css():
    """Inject shared CSS for a consistent, polished look across all pages."""
    st.markdown(
        """
        <style>
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
        </style>
        """,
        unsafe_allow_html=True,
    )
