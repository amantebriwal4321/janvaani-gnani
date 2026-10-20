"""CSC Ready Slip as a one-page PDF. Portal vocabulary is Latin, so a CSC operator can type from it."""

from __future__ import annotations

import io
from datetime import date

import qrcode
from fpdf import FPDF

from app.engine import Brain


def _qr_png(payload: str) -> io.BytesIO:
    image = qrcode.make(payload[:700])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _pdf_text(value: str) -> str:
    """Helvetica is Latin-1. Portal values are English; anything else becomes a readable stand-in."""
    cleaned = value.replace("\u2014", "-").replace("\u2013", "-").replace("\u2019", "'")
    return cleaned.encode("latin-1", "replace").decode("latin-1")


def build_pdf(brain: Brain) -> bytes:
    snap = brain.snapshot()
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_left_margin(12)
    pdf.set_right_margin(46)
    pdf.add_page()

    pdf.set_fill_color(12, 107, 69)
    pdf.rect(0, 0, 210, 26, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(12, 7)
    pdf.cell(130, 8, "JANVAANI   CSC READY SLIP")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(12, 16)
    state = {"ready": "READY FOR THE COUNTER", "draft": "DRAFT  -  CSC CHECKS OPEN", "early": "EARLY DRAFT"}.get(
        snap["slip"], "DRAFT"
    )
    pdf.cell(130, 6, f"{snap['ref']}    {date.today().isoformat()}    {state}")

    pdf.image(_qr_png(snap["share_text"]), x=166, y=30, w=32)

    pdf.set_xy(12, 30)
    pdf.set_text_color(90, 40, 20)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        148,
        4.5,
        "Indicative only. The CSC and the government portal decide. "
        "This is a practice slip. No Aadhaar, PAN, or phone number is printed.",
    )

    pdf.ln(1)
    pdf.set_text_color(20, 18, 16)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "Form values", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    if snap["rows"]:
        for row in snap["rows"]:
            heard = f'   heard: "{row["heard"]}"' if row.get("heard") else ""
            pdf.multi_cell(148, 5, _pdf_text(f"{row['label']}: {row['value']}{heard}"))
    else:
        pdf.multi_cell(148, 5, "Nothing filled yet. Say your place, work, and family on the call.")

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "Schemes to carry", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    shown = [item for item in snap["matches"] if item["status"] in ("qualify", "likely")]
    if not shown:
        pdf.multi_cell(148, 5, "No scheme is confirmed yet.")
    for item in shown:
        mark = "APPLY" if item["status"] == "qualify" else "CHECK"
        reason = item["reasons"][0] if item["reasons"] else ""
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(148, 5, _pdf_text(f"[{mark}] {item['name']}  ({item['authority']})"))
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(148, 5, _pdf_text(f"{reason}  Portal: {item['portal']}"))

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "Papers to carry", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    if snap["documents"]:
        for doc in snap["documents"]:
            pdf.multi_cell(148, 5, _pdf_text(f"- {doc}"))
    else:
        pdf.multi_cell(148, 5, "- Aadhaar, if the CSC asks for it. Do not read the number aloud on this call.")

    if snap["fix_first"]:
        pdf.ln(2)
        pdf.set_fill_color(255, 228, 214)
        pdf.set_text_color(120, 32, 18)
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(148, 6, "Fix this first", fill=True)
        pdf.set_font("Helvetica", "", 10)
        for note in snap["fix_first"]:
            pdf.multi_cell(148, 5, _pdf_text(note), fill=True)
        pdf.set_text_color(20, 18, 16)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "Where to go", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(148, 5, _pdf_text(snap["csc"]))
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(80, 70, 60)
    pdf.multi_cell(148, 4, "Scan the code for the same note you can paste into an SMS or WhatsApp chat. JanVaani does not send the message itself.")
    return bytes(pdf.output())
