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
import requests
import streamlit as st
import streamlit.components.v1 as components
from google.auth.transport.requests import Request
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
USERS_COLUMNS = ["Email", "Tier", "Name", "Phone", "Company", "Role"]
APPROVABLE_TIERS = ["Tier1", "Tier2", "Tier3", "Consumer"]


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_credentials(subject: str | None = None) -> Credentials:
    """Build a fresh Credentials object for direct REST calls (e.g. Drive
    file uploads) that gspread's client doesn't expose a path for.

    If `subject` is given (an email address) and domain-wide delegation has
    been granted for this service account in Google Workspace, the returned
    credentials act AS that user — needed for Drive uploads, since plain
    service accounts have no Drive storage quota of their own."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    if subject:
        creds = creds.with_subject(subject)
    return creds


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


def ensure_worksheet(tab_name: str, headers: list[str]):
    """Get a worksheet, creating it (with a header row) if it doesn't exist yet."""
    ss = get_spreadsheet()
    try:
        return ss.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=tab_name, rows=100, cols=max(len(headers), 2))
        ws.append_row(headers)
        return ws


# ---------------------------------------------------------------------------
# Showcase page content (editable from the Dashboard, stored as simple
# Key/Value rows so new fields can be added later without a schema change)
# ---------------------------------------------------------------------------

SHOWCASE_DEFAULTS = {
    "hero_eyebrow": "Ready-made, by concept",
    "hero_headline": "Every piece is finished and ready. You're choosing a feeling, not a spec sheet.",
    "hero_lead": (
        "Sena doesn't build to order — we hold ready-made concepts in stock, each with its own "
        "wood, fabric, and mood already decided. Pick the one that's you."
    ),
}


def load_showcase_content() -> dict:
    """Load Showcase hero text from the sheet, filling in any missing keys
    with the defaults above so the page never renders blank."""
    content = dict(SHOWCASE_DEFAULTS)
    try:
        df = load_sheet("Showcase")
    except Exception:
        return content
    if not df.empty and "Key" in df.columns and "Value" in df.columns:
        for _, row in df.iterrows():
            key = str(row.get("Key", "")).strip()
            value = row.get("Value", "")
            if key and str(value).strip():
                content[key] = str(value)
    return content


def save_showcase_value(key: str, value: str):
    """Save one Showcase hero-text field. Creates the Showcase tab/row on first use."""
    ensure_worksheet("Showcase", ["Key", "Value"])
    if not update_row_by_match("Showcase", "Key", key, {"Value": value}):
        append_row_generic("Showcase", {"Key": key, "Value": value}, ["Key", "Value"])


# ---------------------------------------------------------------------------
# Showcase concepts (Homey / Insta / Modern, and any the admin adds) — one
# row per concept, so the Dashboard can add, edit, and remove them freely
# instead of being limited to three hardcoded options.
# ---------------------------------------------------------------------------

CONCEPTS_SHEET_COLUMNS = ["ConceptID", "Label", "Keyword", "Mood", "HeroImageURL", "SortOrder"]

DEFAULT_CONCEPTS = [
    {
        "ConceptID": "homey", "Label": "Homey", "Keyword": "homey",
        "Mood": (
            "Warm, deep-seated pieces for a living room you don't want to leave. "
            "Soft edges and generous cushioning, in woods that feel lived-in from day one."
        ),
        "HeroImageURL": "https://drive.google.com/thumbnail?id=17W_pwUonR3nnyDPsvM-i2eVZAGQi6CWM&sz=w1200",
        "SortOrder": 1,
    },
    {
        "ConceptID": "insta", "Label": "Insta", "Keyword": "insta",
        "Mood": (
            "Clean lines and a light palette, built to photograph as well as it sits. "
            "The pieces your living room deserves to be seen in."
        ),
        "HeroImageURL": "https://drive.google.com/thumbnail?id=1mYeQCx08U7RVhdpNvyT8ELXto4j4ytpy&sz=w1200",
        "SortOrder": 2,
    },
    {
        "ConceptID": "modern", "Label": "Modern", "Keyword": "modern",
        "Mood": (
            "Tight, structured silhouettes for smaller spaces that still feel deliberate. "
            "Less footprint, same presence."
        ),
        "HeroImageURL": "https://drive.google.com/thumbnail?id=1knwkTSdYVUbQBAYA98cK0gs0ORT3Ryv_&sz=w1200",
        "SortOrder": 3,
    },
]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower()).strip("-")
    return slug or "concept"


def load_concepts() -> list[dict]:
    """
    Load every Showcase concept, sorted for display. Seeds the Concepts tab
    with the original Homey/Insta/Modern rows on first use (e.g. right after
    upgrading from the old hardcoded version), so nothing goes blank.
    """
    ws = ensure_worksheet("Concepts", CONCEPTS_SHEET_COLUMNS)
    df = load_sheet("Concepts")
    if df.empty:
        for row in DEFAULT_CONCEPTS:
            ws.append_row([row[c] for c in CONCEPTS_SHEET_COLUMNS], value_input_option="USER_ENTERED")
        clear_cache()
        df = load_sheet("Concepts")

    concepts = []
    for _, r in df.iterrows():
        try:
            sort_order = int(r.get("SortOrder", 0) or 0)
        except (TypeError, ValueError):
            sort_order = 0
        concepts.append({
            "id": str(r.get("ConceptID", "")).strip(),
            "label": str(r.get("Label", "")).strip(),
            "keyword": str(r.get("Keyword", "")).strip(),
            "mood": str(r.get("Mood", "")).strip(),
            "hero_image": str(r.get("HeroImageURL", "")).strip(),
            "sort_order": sort_order,
        })
    concepts.sort(key=lambda c: c["sort_order"])
    return concepts


def add_concept(label: str, keyword: str, mood: str, hero_image: str = "") -> str:
    """Add a new concept and return its generated ConceptID."""
    ws = ensure_worksheet("Concepts", CONCEPTS_SHEET_COLUMNS)
    existing = load_concepts()
    existing_ids = {c["id"] for c in existing}

    base_id = _slugify(label)
    concept_id = base_id
    suffix = 2
    while concept_id in existing_ids:
        concept_id = f"{base_id}-{suffix}"
        suffix += 1

    next_sort = (max((c["sort_order"] for c in existing), default=0)) + 1
    ws.append_row(
        [concept_id, label, keyword, mood, hero_image, next_sort],
        value_input_option="USER_ENTERED",
    )
    clear_cache()
    return concept_id


def update_concept(concept_id: str, updates: dict) -> bool:
    """Update one or more fields (Label/Keyword/Mood/HeroImageURL) for a concept."""
    return update_row_by_match("Concepts", "ConceptID", concept_id, updates)


def delete_concept(concept_id: str) -> bool:
    return delete_row_by_match("Concepts", "ConceptID", concept_id)


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


def upload_image_to_drive(file_bytes: bytes, filename: str, mime_type: str) -> str:
    """
    Upload an image straight to Drive and return a ready-to-use thumbnail URL.
    Raises a RuntimeError with Google's actual error detail on failure, so
    the admin sees something actionable rather than a bare "403 Forbidden".

    Plain service accounts have NO Drive storage quota of their own, so a
    direct upload from the service account will always fail with
    storageQuotaExceeded. To fix this for real, set up domain-wide
    delegation for the service account in Google Workspace, then add:
        drive_upload_as_email = "lee@senahome.online"
    to st.secrets — uploads will then be created under that real account's
    Drive (same as your existing Package tab photos), which has quota.
    """
    impersonate_email = st.secrets.get("drive_upload_as_email")
    creds = get_credentials(subject=impersonate_email)
    creds.refresh(Request())
    token = creds.token

    boundary = "sena_showcase_upload"
    metadata = json.dumps({"name": filename})
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{metadata}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--".encode("utf-8")

    upload_resp = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
        data=body,
        timeout=60,
    )
    if not upload_resp.ok:
        raise RuntimeError(f"Drive upload failed ({upload_resp.status_code}): {upload_resp.text}")
    file_id = upload_resp.json()["id"]

    permission_resp = requests.post(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps({"role": "reader", "type": "anyone"}),
        timeout=30,
    )
    if not permission_resp.ok:
        raise RuntimeError(f"Could not make the photo public ({permission_resp.status_code}): {permission_resp.text}")

    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1200"


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


def update_row_by_match(tab_name: str, match_col: str, match_value: str, updates: dict) -> bool:
    """Find the first row in tab_name where match_col == match_value and update the given columns in place."""
    ws = get_spreadsheet().worksheet(tab_name)
    headers = ws.row_values(1)
    if match_col not in headers:
        return False
    match_idx = headers.index(match_col)
    all_values = ws.get_all_values()
    for i, row in enumerate(all_values[1:], start=2):  # row 1 is the header row
        if len(row) > match_idx and row[match_idx].strip().lower() == str(match_value).strip().lower():
            for col_name, new_value in updates.items():
                if col_name in headers:
                    col_idx = headers.index(col_name) + 1
                    ws.update_cell(i, col_idx, new_value)
            clear_cache()
            return True
    return False


def delete_row_by_match(tab_name: str, match_col: str, match_value: str) -> bool:
    """Find the first row in tab_name where match_col == match_value and delete it entirely."""
    ws = get_spreadsheet().worksheet(tab_name)
    headers = ws.row_values(1)
    if match_col not in headers:
        return False
    match_idx = headers.index(match_col)
    all_values = ws.get_all_values()
    for i, row in enumerate(all_values[1:], start=2):  # row 1 is the header row
        if len(row) > match_idx and row[match_idx].strip().lower() == str(match_value).strip().lower():
            ws.delete_rows(i)
            clear_cache()
            return True
    return False


def get_pending_applications() -> pd.DataFrame:
    """Return only the applications still awaiting admin review."""
    try:
        df = load_sheet("Applications")
    except Exception:
        return pd.DataFrame(columns=APPLICATIONS_COLUMNS)
    if df.empty or "Status" not in df.columns:
        return pd.DataFrame(columns=APPLICATIONS_COLUMNS)
    pending = df[df["Status"].astype(str).str.strip().str.lower() == "pending"]
    return pending.reset_index(drop=True)


def approve_application(email: str, tier: str, role: str = "User"):
    """
    Approve a pending applicant: add them to the Users tab with the chosen tier
    (or update their tier if they're already a user), then mark their application Approved.
    """
    application = get_latest_application(email)
    name = application.get("Name", "") if application else ""
    phone = application.get("Phone", "") if application else ""
    company = application.get("Company", "") if application else ""

    if get_user_record(email):
        update_row_by_match("Users", "Email", email, {"Tier": tier})
    else:
        user_row = {
            "Email": email,
            "Tier": tier,
            "Name": name,
            "Phone": phone,
            "Company": company,
            "Role": role,
        }
        append_row_generic("Users", user_row, USERS_COLUMNS)

    update_row_by_match("Applications", "Email", email, {"Status": "Approved"})


def reject_application(email: str):
    """Mark a pending application as rejected without granting access."""
    update_row_by_match("Applications", "Email", email, {"Status": "Rejected"})


LOGO_PATH = "Assets/logo.png"
FACEBOOK_URL = "https://www.facebook.com/profile.php?id=61589913425326"
WHATSAPP_URL = "https://wa.me/60136338923"


def render_contact_widget():
    """Render a floating Cart + Facebook + WhatsApp widget, fixed to the
    real browser viewport.

    This uses components.html rather than st.markdown: st.markdown's
    unsafe_allow_html renders raw HTML via innerHTML under the hood, and
    browsers never execute <script> tags inserted that way (a universal
    rule, not a Streamlit quirk) — so a widget built that way may never
    actually run. components.html renders a real (tiny, invisible) iframe
    document where scripts genuinely execute; the script then reaches into
    window.parent.document so the actual floating buttons attach to the
    real page rather than being trapped inside this small helper iframe.

    The Facebook/WhatsApp icons are only created once (guarded so repeated
    reruns don't duplicate them), but the cart badge count is refreshed on
    every call so it stays live as items are added/removed elsewhere."""
    cart_items = st.session_state.get("cart", [])
    cart_count = sum(int(item.get("qty", 0) or 0) for item in cart_items)

    components.html(
        f"""
        <script>
        (function() {{
            try {{
                var doc = window.parent.document;
                var widget = doc.getElementById('sena-contact-widget');
                if (!widget) {{
                    widget = doc.createElement('div');
                    widget.id = 'sena-contact-widget';
                    widget.style.position = 'fixed';
                    widget.style.bottom = '90px';
                    widget.style.right = '24px';
                    widget.style.display = 'flex';
                    widget.style.flexDirection = 'column';
                    widget.style.gap = '12px';
                    widget.style.zIndex = '999999';
                    widget.innerHTML =
                        '<a href="?goto=cart" ' +
                        'style="position:relative;width:52px;height:52px;border-radius:50%;display:flex;' +
                        'align-items:center;justify-content:center;background:#2B1D14;border:1px solid #5C3A21;' +
                        'color:#F3EAD8;font-size:1.4rem;text-decoration:none;' +
                        'box-shadow:0 4px 14px rgba(0,0,0,0.25);">🛒' +
                        '<span id="sena-cart-badge" style="position:absolute;top:-4px;right:-4px;' +
                        'min-width:20px;height:20px;border-radius:10px;background:#C9A227;color:#2B1D14;' +
                        'font-size:0.72rem;font-weight:800;display:none;align-items:center;justify-content:center;' +
                        'padding:0 5px;font-family:sans-serif;"></span></a>' +
                        '<a href="{FACEBOOK_URL}" target="_blank" rel="noopener" ' +
                        'style="width:52px;height:52px;border-radius:50%;display:flex;' +
                        'align-items:center;justify-content:center;background:#1877F2;' +
                        'color:#fff;font-weight:800;font-size:1.5rem;font-family:Georgia,serif;' +
                        'text-decoration:none;box-shadow:0 4px 14px rgba(0,0,0,0.25);">f</a>' +
                        '<a href="{WHATSAPP_URL}" target="_blank" rel="noopener" ' +
                        'style="width:52px;height:52px;border-radius:50%;display:flex;' +
                        'align-items:center;justify-content:center;background:#25D366;' +
                        'color:#fff;font-size:1.5rem;text-decoration:none;' +
                        'box-shadow:0 4px 14px rgba(0,0,0,0.25);">💬</a>';
                    doc.body.appendChild(widget);
                }}
                var badge = doc.getElementById('sena-cart-badge');
                if (badge) {{
                    var count = {cart_count};
                    if (count > 0) {{
                        badge.textContent = count;
                        badge.style.display = 'flex';
                    }} else {{
                        badge.style.display = 'none';
                    }}
                }}
            }} catch (e) {{
                // TEMPORARY diagnostic — remove once the widget is confirmed working.
                alert('Sena widget error: ' + e.name + ': ' + e.message);
            }}
        }})();
        </script>
        """,
        height=1,
    )


def render_brand_header(title: str, subtitle: str = ""):
    """Render the page title and subtitle. The logo now lives in the top navbar."""
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)
    st.write("")


def render_sidebar_logo():
    """Render a small logo at the top of the sidebar for consistent branding."""
    with st.sidebar:
        st.image(LOGO_PATH, width="stretch")
        st.write("---")


def build_nav_pages(viewer_is_admin: bool) -> list:
    """
    Single source of truth for the app's page list, used both by the router
    (app.py, for st.navigation) and by render_top_navbar (for the matching
    page_link buttons), so the two never drift out of sync.

    Showcase is the landing page for everyone (default=True) and sits first
    in the nav order, since it's the public-facing front door to the catalog.
    """
    pages = []
    pages.append(st.Page("pages/4_Showcase.py", title="Showcase", icon="✨", default=True))
    if viewer_is_admin:
        pages.append(st.Page("pages/0_Dashboard.py", title="Dashboard", icon="📊"))
    pages.append(st.Page("pages/1_Catalog.py", title="Catalog", icon="🛋️"))
    pages.append(st.Page("pages/2_Cart.py", title="Cart", icon="🛒"))
    pages.append(st.Page("pages/3_Order_History.py", title="Order History", icon="📦"))
    return pages


def render_top_navbar(user_record: dict, pages: list):
    """
    Render one professional horizontal navbar — logo, page links, the current
    user's name/tier, and a logout control — replacing the sidebar entirely.
    Call this near the top of every page, right after gate_access().
    """
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }

        /* Scope everything to the row that actually contains our page links,
           so this never affects unrelated column rows elsewhere in the app. */
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) {
            background-color: #2B1D14;
            border-radius: 14px;
            padding: 14px 20px;
        }
        /* Let nav links hug each other instead of stretching across the
           whole nav column, which was leaving a large empty gap before
           the user/logout area. */
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) div[data-testid="stHorizontalBlock"] {
            gap: 6px !important;
            justify-content: flex-start !important;
        }
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) div[data-testid="stHorizontalBlock"] > div {
            flex: 0 0 auto !important;
            width: auto !important;
        }

        .sena-navbar-rule {
            margin: 0 0 1.4rem 0;
        }
        .sena-user-chip {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 8px;
            font-size: 0.9rem;
            color: #F3EAD8 !important;
            white-space: nowrap;
        }
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) div[data-testid="stPageLink"] a {
            border-radius: 8px;
            font-weight: 600;
            color: #F3EAD8 !important;
        }
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) div[data-testid="stPageLink"] a:hover {
            background-color: rgba(255, 255, 255, 0.08);
        }
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) button {
            background-color: transparent !important;
            border: 1px solid #5C3A21 !important;
            color: #F3EAD8 !important;
        }
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) button:hover {
            border-color: #C9A227 !important;
            color: #C9A227 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    logo_col, nav_col, user_col, logout_col = st.columns(
        [1.1, 2.6, 1.6, 0.8], vertical_alignment="center"
    )

    with logo_col:
        st.image(LOGO_PATH, width=140)

    with nav_col:
        if pages:
            link_cols = st.columns(len(pages))
            for link_col, page in zip(link_cols, pages):
                with link_col:
                    st.page_link(page, label=page.title, icon=page.icon)
        else:
            st.caption("Navigation unavailable — please refresh the page.")

    with user_col:
        name = user_record.get("Name") or user_record.get("Email", "")
        tier = user_record.get("Tier", "")
        st.markdown(
            f"""<div class="sena-user-chip">👤 <b>{name}</b>
                <span class="tier-badge">{tier}</span></div>""",
            unsafe_allow_html=True,
        )

    with logout_col:
        if st.session_state.get("guest_mode"):
            if st.button("Exit", width="stretch", key="navbar_exit_guest"):
                st.session_state.pop("guest_mode", None)
                st.rerun()
        else:
            if st.button("Log out", width="stretch", key="navbar_logout"):
                st.logout()

    st.markdown('<div class="sena-navbar-rule"></div>', unsafe_allow_html=True)


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
            if st.button("Exit Guest Mode", width="stretch"):
                st.session_state.pop("guest_mode", None)
                st.rerun()
        else:
            if st.button("Log out", width="stretch"):
                st.logout()
        st.write("---")


# ---------------------------------------------------------------------------
# Shared visual styling
# ---------------------------------------------------------------------------

def apply_custom_css():
    """Inject shared CSS for a consistent, polished look across all pages."""
    st.markdown(
        """
        <script>
        (function() {
            var meta = document.querySelector('meta[name="color-scheme"]');
            if (!meta) {
                meta = document.createElement('meta');
                meta.name = 'color-scheme';
                document.head.appendChild(meta);
            }
            meta.content = 'light only';
            document.documentElement.style.colorScheme = 'light';
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        :root, html, body, .stApp {
            color-scheme: light only;
            forced-color-adjust: none;
        }
        .stApp { background-color: #2B1D14; }

        h1, h2, h3 { color: #F3EAD8; font-weight: 700; }

        .kpi-card {
            background: #3A2A1C;
            border-radius: 16px;
            padding: 1.3rem 1.5rem;
            border: 1px solid #5C3A21;
            box-shadow: 0 2px 12px rgba(0,0,0,0.2);
        }
        .kpi-label { font-size: 0.82rem; color: #C9A66B; font-weight: 600; letter-spacing: 0.02em; text-transform: uppercase; margin-bottom: 0.35rem; }
        .kpi-value { font-size: 1.9rem; font-weight: 800; color: #F3EAD8; }

        .product-card {
            background: #3A2A1C;
            border-radius: 18px;
            border: 1px solid #5C3A21;
            box-shadow: 0 2px 10px rgba(0,0,0,0.18);
            overflow: hidden;
            transition: box-shadow 0.15s ease;
        }
        .product-image-wrap {
            width: 100%;
            height: 200px;
            overflow: hidden;
            border-radius: 14px;
            background: #2B1D14;
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
            color: #C9A227;
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
            color: #D8CBB4;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-top: 6px;
        }
        .price-strike {
            font-size: 0.95rem;
            font-weight: 600;
            color: #D8CBB4;
            text-decoration: line-through;
        }
        .size-badge-row {
            min-height: 26px;
            margin-bottom: 8px;
            display: block;
        }
        .size-badge {
            background: #5C3A21;
            color: #C9A66B;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.72rem;
            font-weight: 600;
            display: inline-block;
        }
        .tier-badge {
            background: #4B5D45;
            color: #F3EAD8;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-block;
        }

        section[data-testid="stSidebar"] {
            background-color: #3A2A1C;
            border-right: 1px solid #5C3A21;
        }

        div[data-testid="stButton"] button {
            border-radius: 10px;
            font-weight: 600;
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background-color: #C9A227;
            border-color: #C9A227;
            color: #2B1D14 !important;
        }

        [data-testid="stExpander"] {
            border-radius: 14px;
            border: 1px solid #5C3A21;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
