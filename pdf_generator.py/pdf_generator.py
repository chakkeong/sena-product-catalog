"""
PDF Purchase Order generator for Sena Product Catalog.

Produces a branded, professional-looking Purchase Order PDF for any order,
using the existing company logo (Assets/logo.png) and company details below.

EDIT THE COMPANY_* CONSTANTS BELOW WITH YOUR REAL DETAILS before deploying.
"""

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)

# ---------------------------------------------------------------------------
# EDIT THESE WITH YOUR ACTUAL COMPANY DETAILS
# ---------------------------------------------------------------------------
COMPANY_NAME = "Sena Home Solution"
COMPANY_ADDRESS_LINES = [
    "AZ A3A-02, LEVEL 3A, BLOCK A,",
    "ANZEN BUSINESS PARK, JALAN 4/37A,",
    "TAMAN INDUSTRI BUKIT MALURI,",
    "52100 KEPONG, KUALA LUMPUR",
]
COMPANY_PHONE = "+60 13-633 8923"
COMPANY_EMAIL = "lee@senahome.online"
COMPANY_WEBSITE = "www.senahome.online"
COMPANY_REG_NO = "Reg. No: 202503169281 (NIS0310717-X)"
BANK_DETAILS_LINES = [
    # Leave this list empty to omit the "Payment Details" box entirely.
    # "Bank: Example Bank Berhad",
    # "Account Name: Sena Home Solution",
    # "Account No: 1234 5678 9012",
]
LOGO_PATH = "Assets/logo.png"

BRAND_NAVY = colors.HexColor("#111827")
BRAND_INDIGO = colors.HexColor("#4F46E5")
BRAND_GRAY = colors.HexColor("#6B7280")
BRAND_LIGHT_BG = colors.HexColor("#F3F4F6")


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "company_name": ParagraphStyle(
            "company_name", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=15, textColor=BRAND_NAVY, leading=18,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, textColor=BRAND_GRAY, leading=12,
        ),
        "po_title": ParagraphStyle(
            "po_title", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=20, textColor=BRAND_NAVY, alignment=TA_RIGHT, leading=24,
        ),
        "po_meta": ParagraphStyle(
            "po_meta", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=BRAND_NAVY, alignment=TA_RIGHT, leading=14,
        ),
        "section_label": ParagraphStyle(
            "section_label", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8.5, textColor=BRAND_GRAY, leading=11,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Helvetica",
            fontSize=10, textColor=BRAND_NAVY, leading=14,
        ),
        "table_header": ParagraphStyle(
            "table_header", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, textColor=colors.white, leading=12,
        ),
        "table_cell": ParagraphStyle(
            "table_cell", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=BRAND_NAVY, leading=13,
        ),
        "total_label": ParagraphStyle(
            "total_label", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, textColor=BRAND_NAVY, alignment=TA_RIGHT,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, textColor=BRAND_GRAY, leading=11,
        ),
    }
    return styles


def _format_currency(value) -> str:
    try:
        return f"RM {float(value):,.2f}"
    except (TypeError, ValueError):
        return f"RM {value}"


def generate_po_pdf(
    po_number: str,
    customer_name: str,
    customer_email: str,
    customer_company: str,
    customer_phone: str,
    tier: str,
    status: str,
    timestamp: str,
    items: list[dict],
    total: float,
    version: int = 1,
) -> bytes:
    """
    Build a branded Purchase Order PDF and return it as raw bytes,
    ready to hand to st.download_button.

    items: list of dicts like {"name": ..., "size": ..., "qty": ..., "price": ...}
    """
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    story = []

    # ----- Header: logo + company info (left) | PO title + meta (right) -----
    try:
        if os.path.isfile(LOGO_PATH):
            logo = Image(LOGO_PATH, width=42 * mm, height=14 * mm)
            logo.hAlign = "LEFT"
        else:
            logo = Paragraph(COMPANY_NAME, styles["company_name"])
    except Exception:
        logo = Paragraph(COMPANY_NAME, styles["company_name"])

    company_block = [logo, Spacer(1, 4)]
    for line in COMPANY_ADDRESS_LINES:
        company_block.append(Paragraph(line, styles["small"]))
    if COMPANY_REG_NO:
        company_block.append(Spacer(1, 2))
        company_block.append(Paragraph(COMPANY_REG_NO, styles["small"]))

    po_meta_lines = [
        f"PO Number: <b>{po_number}</b>",
        f"Date: {timestamp}",
        f"Status: {status}",
        f"Tier: {tier}",
    ]
    if version and version > 1:
        po_meta_lines.append(f"Version: {version}")

    header_right = [
        Paragraph("PURCHASE ORDER", styles["po_title"]),
        Spacer(1, 6),
        Paragraph("<br/>".join(po_meta_lines), styles["po_meta"]),
    ]

    header_table = Table(
        [[company_block, header_right]],
        colWidths=[100 * mm, 70 * mm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.2, color=BRAND_INDIGO))
    story.append(Spacer(1, 14))

    # ----- Billed To -----
    story.append(Paragraph("BILLED TO", styles["section_label"]))
    story.append(Spacer(1, 3))
    billed_lines = [customer_name or customer_email]
    if customer_company:
        billed_lines.append(customer_company)
    billed_lines.append(customer_email)
    if customer_phone:
        billed_lines.append(customer_phone)
    story.append(Paragraph("<br/>".join(billed_lines), styles["body"]))
    story.append(Spacer(1, 18))

    # ----- Line items table -----
    table_data = [[
        Paragraph("Product", styles["table_header"]),
        Paragraph("Size", styles["table_header"]),
        Paragraph("Qty", styles["table_header"]),
        Paragraph("Unit Price", styles["table_header"]),
        Paragraph("Line Total", styles["table_header"]),
    ]]

    for item in items:
        qty = item.get("qty", 0)
        price = float(item.get("price", 0) or 0)
        line_total = qty * price
        table_data.append([
            Paragraph(str(item.get("name", "")), styles["table_cell"]),
            Paragraph(str(item.get("size", "") or "—"), styles["table_cell"]),
            Paragraph(str(qty), styles["table_cell"]),
            Paragraph(_format_currency(price), styles["table_cell"]),
            Paragraph(_format_currency(line_total), styles["table_cell"]),
        ])

    items_table = Table(
        table_data,
        colWidths=[70 * mm, 28 * mm, 18 * mm, 28 * mm, 30 * mm],
        repeatRows=1,
    )
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT_BG]),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (-1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # ----- Total -----
    total_table = Table(
        [["", Paragraph(f"TOTAL: {_format_currency(total)}", styles["total_label"])]],
        colWidths=[104 * mm, 70 * mm],
    )
    total_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEABOVE", (1, 0), (1, 0), 1, BRAND_INDIGO),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 24))

    # ----- Payment details (optional) -----
    if BANK_DETAILS_LINES:
        story.append(Paragraph("PAYMENT DETAILS", styles["section_label"]))
        story.append(Spacer(1, 3))
        story.append(Paragraph("<br/>".join(BANK_DETAILS_LINES), styles["body"]))
        story.append(Spacer(1, 18))

    # ----- Footer -----
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Phone: {COMPANY_PHONE}  ·  Email: {COMPANY_EMAIL}  ·  Website: {COMPANY_WEBSITE}",
        styles["footer"],
    ))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        f"This document was generated automatically by {COMPANY_NAME} on "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}. For questions about this "
        f"order, contact us using the details above.",
        styles["footer"],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
