# Sena Product Catalog

A Streamlit dashboard for tiered pricing & purchase orders, backed by your existing Google Sheet.

## What's included
- `app.py` — Dashboard (KPIs + charts)
- `pages/1_Catalog.py` — Product search & add to cart (tiered pricing)
- `pages/2_Cart.py` — Cart review & PO submission
- `pages/3_Order_History.py` — PO history with version-preserving amendments
- `utils.py` — Google Sheets connection & shared logic
- `requirements.txt` — Python dependencies
- `.streamlit/secrets_template.toml` — Shows what secrets you'll need (don't fill this file in — use Streamlit Cloud's Secrets panel instead)

## Sheet requirements
Your Google Sheet needs these exact tab names: **Users**, **Products**, **Orders**

**Products** columns: `ProductID, Name, Description, Tier1Price, Tier2Price, Tier3Price, ConsumerPrice, ImageURL, Size/Measurement`

**Users** columns: `UserID, Name, Email, Tier, Status` (Tier = Tier1/Tier2/Tier3/Consumer/Guest)

**Orders** columns (the app creates this header row automatically if missing):
`PONumber, OrderID, UserID, ProductID, ProductName, Qty, UnitPrice, LineTotal, Version, Timestamp, Status`

If your Users tab has different column names, just rename them to match — the app reads by header name.

## Setup steps

### 1. Get your Sheet ID
Open your Google Sheet. The ID is the long string in the URL between `/d/` and `/edit`:
`https://docs.google.com/spreadsheets/d/THIS_PART_IS_YOUR_SHEET_ID/edit`

### 2. Push this folder to GitHub
1. Go to github.com → click **+** (top right) → **New repository**
2. Name it `sena-product-catalog` → set to **Public** or **Private** (either works) → Create repository
3. On the new repo page, click **uploading an existing file**
4. Drag in all the files from this folder (keep the `pages` folder structure intact)
5. Commit the files

### 3. Deploy on Streamlit Community Cloud
1. Go to share.streamlit.io → **Create app**
2. Choose **Deploy a public app from GitHub** (or your repo)
3. Select your `sena-product-catalog` repo, branch `main`, main file path `app.py`
4. Click **Advanced settings** → find the **Secrets** box
5. Paste in this structure, filling in your real values from the service account JSON file:

```
sheet_id = "paste-your-sheet-id-here"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Copy each value straight from your downloaded `.json` key file — every field has a matching name.

6. Click **Deploy**
7. Wait 1-2 minutes — your app will build and go live with a `streamlit.app` URL

### 4. Test it
- Visit your app URL
- Check the Dashboard loads (it'll show zeros if Orders is empty — that's expected)
- Go to Catalog, search for a product, add to cart
- Go to Cart, submit a test PO
- Go to Order History, confirm it shows up, try amending it (qty change) and confirm a new version appears

## Updating the app later
Any time you want to change the code: edit the file on GitHub directly (or re-upload it), and Streamlit Cloud will automatically redeploy within a minute or two.
