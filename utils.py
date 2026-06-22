"""
Shared utilities for Sena Product Catalog.
Handles Google Sheets connection, data loading/saving, pricing logic,
and PO number / version generation.
"""

import re
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
    "Guest": "ConsumerPrice",  # Guests see consumer pricing
}

ORDERS_COLUMNS = [
    "PONumber", "OrderID", "UserID", "ProductID", "ProductName",
    "Qty", "UnitPrice", "LineTotal", "Version", "Timestamp", "Status",
]


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_client():
    """Authenticate with Google using the service account stored in secrets."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_spreadsheet():
    """Open the spreadsheet by its ID (set in secrets.toml as `sheet_id`)."""
    client = get_client()
    return client.open_by_key(st.secrets["sheet_id"])


# ---------------------------------------------------------------------------
# Loading data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def load_sheet(tab_name: str) -> pd.DataFrame:
    """Load a worksheet tab into a pandas DataFrame."""
    ws = get_spreadsheet().worksheet(tab_name)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    return df


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
    for col in ["Qty", "UnitPrice", "LineTotal", "Version"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def clear_cache():
    load_sheet.clear()


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

def get_price_for_tier(product_row: pd.Series, tier: str) -> float:
    """Return the correct unit price for a product given a user tier."""
    col = TIER_PRICE_COLUMN.get(tier, "ConsumerPrice")
    return float(product_row.get(col, 0) or 0)


def drive_thumbnail_url(image_url: str) -> str:
    """Convert a Google Drive share link into a thumbnail-rendering URL."""
    if not image_url:
        return ""
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", image_url)
    if not match:
        match = re.search(r"id=([a-zA-Z0-9_-]+)", image_url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
    return image_url


# ---------------------------------------------------------------------------
# PO numbering / versioning
# ---------------------------------------------------------------------------

def generate_po_number(orders_df: pd.DataFrame) -> str:
    """Generate the next auto-incremented PO number, e.g. PO-0001."""
    if orders_df.empty or "PONumber" not in orders_df.columns:
        return "PO-0001"
    numbers = []
    for po in orders_df["PONumber"].dropna().unique():
        m = re.search(r"(\d+)$", str(po))
        if m:
            numbers.append(int(m.group(1)))
    next_num = (max(numbers) + 1) if numbers else 1
    return f"PO-{next_num:04d}"


def get_next_version(orders_df: pd.DataFrame, po_number: str) -> int:
    """Get the next version number for an existing PO (for amendments)."""
    if orders_df.empty:
        return 1
    existing = orders_df[orders_df["PONumber"] == po_number]
    if existing.empty:
        return 1
    return int(existing["Version"].max()) + 1


def latest_versions_only(orders_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse the orders table down to only the latest version of each PO."""
    if orders_df.empty:
        return orders_df
    idx = orders_df.groupby("PONumber")["Version"].idxmax()
    return orders_df.loc[idx].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Writing data
# ---------------------------------------------------------------------------

def append_order_rows(rows: list[dict]):
    """Append new order line rows to the Orders sheet. Never overwrites history."""
    ws = get_spreadsheet().worksheet("Orders")
    existing_headers = ws.row_values(1)
    if not existing_headers:
        ws.append_row(ORDERS_COLUMNS)
        existing_headers = ORDERS_COLUMNS
    for row in rows:
        ordered_row = [row.get(col, "") for col in existing_headers]
        ws.append_row(ordered_row, value_input_option="USER_ENTERED")
    clear_cache()


def timestamp_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
