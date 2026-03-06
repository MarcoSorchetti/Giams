"""
Generazione PDF Report Costi per riscontro bancario — GIAMS
"""
import io
from datetime import date
from fpdf import FPDF

from app.services.pdf_vendita import AZIENDA, LOGO_PATH, DocumentoPDF, _fmt


def genera_report_costi_pdf(costi_data: list, data_da: date = None, data_a: date = None, label_periodo: str = "") -> bytes:
    """Genera PDF del report costi ordinato per data pagamento."""

    titolo = "REPORT COSTI - RISCONTRO BANCARIO"
    pdf = DocumentoPDF(titolo_doc=titolo)
    pdf.alias_nb_pages()
    pdf.add_page("L")  # Landscape per avere piu' spazio

    # Periodo
    pdf.set_font("Helvetica", "", 9)
    if label_periodo:
        periodo_str = label_periodo
    elif data_da and data_a:
        periodo_str = f"Dal {data_da.strftime('%d/%m/%Y')} al {data_a.strftime('%d/%m/%Y')}"
    elif data_da:
        periodo_str = f"Dal {data_da.strftime('%d/%m/%Y')}"
    elif data_a:
        periodo_str = f"Fino al {data_a.strftime('%d/%m/%Y')}"
    else:
        periodo_str = "Tutti i costi"
    pdf.cell(0, 5, f"Periodo: {periodo_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Generato il: {date.today().strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Intestazione tabella
    pdf.set_font("Helvetica", "B", 7)
    col_w = [22, 22, 60, 50, 25, 20, 22, 28, 28]
    headers = ["Data Pag.", "Data Fatt.", "Descrizione", "Fornitore", "N. Fattura", "Tipo Doc.", "Imponibile", "IVA", "Totale"]

    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, border=1, align="C")
    pdf.ln()

    # Righe
    pdf.set_font("Helvetica", "", 7)
    totale_imponibile = 0
    totale_iva = 0
    totale_importo = 0

    for c in costi_data:
        data_pag = c["data_pagamento"].strftime("%d/%m/%Y") if c["data_pagamento"] else "—"
        data_fat = c["data_fattura"].strftime("%d/%m/%Y") if c["data_fattura"] else "—"
        descrizione = (c["descrizione"] or "")[:40]
        fornitore = (c["fornitore"] or "")[:32]
        num_fatt = (c["numero_fattura"] or "")[:16]
        tipo_doc = (c["tipo_documento_label"] or c["tipo_documento"] or "")[:14]
        imponibile = float(c["imponibile"])
        importo_iva = float(c["importo_iva"])
        importo_tot = float(c["importo_totale"])

        totale_imponibile += imponibile
        totale_iva += importo_iva
        totale_importo += importo_tot

        pdf.cell(col_w[0], 5, data_pag, border=1, align="C")
        pdf.cell(col_w[1], 5, data_fat, border=1, align="C")
        pdf.cell(col_w[2], 5, descrizione, border=1)
        pdf.cell(col_w[3], 5, fornitore, border=1)
        pdf.cell(col_w[4], 5, num_fatt, border=1)
        pdf.cell(col_w[5], 5, tipo_doc, border=1, align="C")
        pdf.cell(col_w[6], 5, _fmt(imponibile), border=1, align="R")
        pdf.cell(col_w[7], 5, _fmt(importo_iva), border=1, align="R")
        pdf.cell(col_w[8], 5, _fmt(importo_tot), border=1, align="R")
        pdf.ln()

    # Riga totali
    pdf.set_font("Helvetica", "B", 8)
    sum_label_w = sum(col_w[:6])
    pdf.cell(sum_label_w, 7, f"TOTALE ({len(costi_data)} voci)", border=1, align="R")
    pdf.cell(col_w[6], 7, _fmt(totale_imponibile), border=1, align="R")
    pdf.cell(col_w[7], 7, _fmt(totale_iva), border=1, align="R")
    pdf.cell(col_w[8], 7, _fmt(totale_importo), border=1, align="R")
    pdf.ln()

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
