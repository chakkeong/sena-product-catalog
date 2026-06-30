"""
auth.py — Authentication & role/tier access module for Sena Product Catalog
(Streamlit + Google Sheets)

Sheet: https://docs.google.com/spreadsheets/d/1QdsRtl9GCdQc5OiyMeZ1JJc8DjPUx6WpUBoHzCLk814
Tab:   Users

Columns (in order): Email | Tier | Name | Phone | Company | Role | Password | Status

Notes:
- Password is stored in PLAIN TEXT for now (per current decision). See
  migrate_to_hashed() at the bottom for an easy upgrade path later.
- Tier values in the sheet are kept as-is: "Tier1", "Tier2", "Tier3", "Consumer".
  TIER_DISPLAY / TIER_PRICE_COL map these to pricing columns in the Products sheet.
- Role values: "Admin" / "User" (case-insensitive matched in code).
- Status values: "active" / "pending" / "disabled".
  Existing rows with no Status are treated as "active" (see ensure_schema()).
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1QdsRtl9GCdQc5OiyMeZ1JJc8DjPUx6WpUBoHzCLk814"
USERS_TAB = "Users"

# Column order — must match the sheet. If you add/reorder columns, update this.
COLUMNS = ["Email", "Tier", "Name", "Phone", "Company", "Role", "Password", "Status"]

TIER_TO_PRICE_COL = {
    "tier1": "Tier1Price",
    "tier2": "Tier2Price",
    "tier3": "Tier3Price",
    "consumer": "ConsumerPrice",
    "guest": "ConsumerPrice",
    "pending": "ConsumerPrice",  # fallback while awaiting approval
}

TEMP_PASSWORD_FOR_EXISTING_USERS = "welcome123"


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds)


def get_users_worksheet():
    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(USERS_TAB)


def load_users_df():
    """Returns the Users tab as a pandas DataFrame, column order normalized."""
    import pandas as pd

    ws = get_users_worksheet()
    records = ws.get_all_records()
    df = pd.DataFrame(records)

    # Ensure all expected columns exist even if sheet is missing some
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[COLUMNS]


# ---------------------------------------------------------------------------
# One-time schema fix-up for your existing sheet
# ---------------------------------------------------------------------------

def ensure_schema():
    """
    Adds 'Password' and 'Status' headers if missing, and backfills existing
    rows (the 5 pre-existing accounts) with a temp password + active status.
    Safe to call every app run — it no-ops once the sheet is already migrated.
    """
    ws = get_users_worksheet()
    header = ws.row_values(1)

    changed_header = False
    if "Password" not in header:
        ws.update_cell(1, len(header) + 1, "Password")
        header.append("Password")
        changed_header = True
    if "Status" not in header:
        ws.update_cell(1, len(header) + 1, "Status")
        header.append("Status")
        changed_header = True

    if changed_header:
        header = ws.row_values(1)  # re-read in case both were added

    pw_col = header.index("Password") + 1
    status_col = header.index("Status") + 1

    all_values = ws.get_all_values()
    for i, row in enumerate(all_values[1:], start=2):  # row 1 = header
        # Pad row in case it's shorter than header
        row = row + [""] * (len(header) - len(row))
        existing_password = row[pw_col - 1].strip()
        existing_status = row[status_col - 1].strip()

        if not existing_password:
            ws.update_cell(i, pw_col, TEMP_PASSWORD_FOR_EXISTING_USERS)
        if not existing_status:
            ws.update_cell(i, status_col, "active")


# ---------------------------------------------------------------------------
# Signup / Login
# ---------------------------------------------------------------------------

def signup(email: str, password: str, name: str, phone: str = "", company: str = ""):
    """Self-signup: new users land as Role=User, Tier=pending, Status=pending."""
    email = email.strip().lower()
    df = load_users_df()

    if email in df["Email"].str.strip().str.lower().values:
        return False, "Email already registered."
    if not email or not password or not name:
        return False, "Name, email, and password are required."

    ws = get_users_worksheet()
    # Order must match COLUMNS exactly
    ws.append_row([email, "pending", name, phone, company, "User", password, "pending"])
    return True, "Account created. An admin needs to approve your account before you can log in."


def login(email: str, password: str):
    """Returns (user_row_dict, error_message). user_row_dict is None on failure."""
    email = email.strip().lower()
    df = load_users_df()

    match = df[df["Email"].str.strip().str.lower() == email]
    if match.empty:
        return None, "Invalid email or password."

    row = match.iloc[0]
    if str(row["Password"]) != password:
        return None, "Invalid email or password."

    status = str(row["Status"]).strip().lower()
    if status == "pending":
        return None, "Your account is pending admin approval."
    if status == "disabled":
        return None, "Your account has been disabled. Contact an admin."

    return row.to_dict(), None


def logout():
    for key in ("sena_user",):
        if key in st.session_state:
            del st.session_state[key]


# ---------------------------------------------------------------------------
# Role / tier helpers
# ---------------------------------------------------------------------------

def is_admin(user: dict) -> bool:
    return str(user.get("Role", "")).strip().lower() == "admin"


def get_price_column(user: dict) -> str:
    """Maps a user's Tier value to the matching price column in the Products sheet."""
    tier = str(user.get("Tier", "")).strip().lower()
    return TIER_TO_PRICE_COL.get(tier, "ConsumerPrice")


def require_login():
    """Call at the top of a page. Stops the script if not logged in."""
    if "sena_user" not in st.session_state:
        st.warning("Please log in to continue.")
        st.stop()
    return st.session_state["sena_user"]


def require_admin():
    """Call at the top of an admin-only page. Stops the script if not admin."""
    user = require_login()
    if not is_admin(user):
        st.error("Admin access only.")
        st.stop()
    return user


# ---------------------------------------------------------------------------
# Admin actions: approve / edit / disable users
# ---------------------------------------------------------------------------

def update_user(email: str, **fields):
    """
    Updates one or more fields for a user row, matched by Email.
    e.g. update_user("foo@bar.com", Status="active", Tier="Tier1")
    """
    ws = get_users_worksheet()
    header = ws.row_values(1)
    all_values = ws.get_all_values()

    email_col = header.index("Email")
    target_row = None
    for i, row in enumerate(all_values[1:], start=2):
        if row[email_col].strip().lower() == email.strip().lower():
            target_row = i
            break

    if target_row is None:
        return False, "User not found."

    for field, value in fields.items():
        if field not in header:
            continue
        col = header.index(field) + 1
        ws.update_cell(target_row, col, value)

    return True, "Updated."


def list_pending_users():
    df = load_users_df()
    return df[df["Status"].str.strip().str.lower() == "pending"]


def delete_user(email: str):
    ws = get_users_worksheet()
    all_values = ws.get_all_values()
    header = all_values[0]
    email_col = header.index("Email")

    for i, row in enumerate(all_values[1:], start=2):
        if row[email_col].strip().lower() == email.strip().lower():
            ws.delete_rows(i)
            return True, "User deleted."
    return False, "User not found."


# ---------------------------------------------------------------------------
# Migration: plain text -> hashed passwords (run later, once, manually)
# ---------------------------------------------------------------------------

def migrate_to_hashed():
    """
    One-time migration. Call this manually (e.g. from a temporary admin
    button or a standalone script) when you're ready to switch from plain
    text to sha256 hashed passwords. After running this, update login()
    and signup() to hash the password before comparing/storing:

        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()
    """
    import hashlib

    ws = get_users_worksheet()
    header = ws.row_values(1)
    pw_col = header.index("Password") + 1
    all_values = ws.get_all_values()

    for i, row in enumerate(all_values[1:], start=2):
        plain = row[pw_col - 1]
        if not plain:
            continue
        # Skip if already looks like a sha256 hash (64 hex chars)
        if len(plain) == 64 and all(c in "0123456789abcdef" for c in plain.lower()):
            continue
        hashed = hashlib.sha256(plain.encode()).hexdigest()
        ws.update_cell(i, pw_col, hashed)
