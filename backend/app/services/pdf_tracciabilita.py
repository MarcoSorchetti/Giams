"""
Generazione PDF scheda tracciabilita' lotto - GIAMS
"""
import io
from sqlalchemy.orm import Session

from app.services.pdf_vendita import DocumentoPDF, get_azienda_data, _AZIENDA_DEFAULT


def genera_tracciabilita_pdf(data: dict, db: Session = None) -> bytes:
    """Genera il PDF della scheda di tracciabilita' per un lotto."""
    az = get_azienda_data(db) if db else _AZIENDA_DEFAULT
    lotto = data["lotto"]
    racc = data["raccolta"]
    parcelle = data["parcelle"]
    confs = data["confezionamenti"]
    vendite = data["vendite"]
    riep = data["riepilogo"]

    titolo = f"Scheda Tracciabilita' - Lotto {lotto['codice_lotto']}"
    pdf = DocumentoPDF(titolo_doc=titolo, azienda=az)
    pdf.alias_nb_pages()
    pdf.add_page()
    pw = pdf.w - pdf.l_margin - pdf.r_margin  # larghezza utile

    # --- SEZIONE 1: DATI LOTTO ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(40, 60, 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(pw, 7, "  DATI LOTTO", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 9)
    _riga_pdf(pdf, "Codice Lotto:", lotto["codice_lotto"], pw)
    _riga_pdf(pdf, "Anno Campagna:", f"{lotto['anno_campagna']}/{lotto['anno_campagna'] + 1}", pw)
    _riga_pdf(pdf, "Tipo Olio:", lotto["tipo_olio"], pw)
    if lotto.get("certificazione"):
        _riga_pdf(pdf, "Certificazione:", lotto["certificazione"], pw)
    _riga_pdf(pdf, "Data Molitura:", _fmt_data(lotto["data_molitura"]), pw)
    _riga_pdf(pdf, "Kg Olive:", f"{lotto['kg_olive']:.1f} kg", pw)
    _riga_pdf(pdf, "Litri Olio:", f"{lotto['litri_olio']:.1f} L", pw)
    resa = lotto.get("resa_percentuale")
    _riga_pdf(pdf, "Resa:", f"{resa:.1f}%" if resa else "n/d", pw)
    if lotto.get("frantoio"):
        fr = lotto["frantoio"]
        _riga_pdf(pdf, "Frantoio:", f"{fr['denominazione']}{' - ' + fr['citta'] if fr.get('citta') else ''}", pw)
    pdf.ln(3)

    # --- SEZIONE 2: ORIGINE (RACCOLTA + PARCELLE) ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(40, 60, 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(pw, 7, "  ORIGINE - RACCOLTA E PARCELLE", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    if racc:
        pdf.set_font("Helvetica", "", 9)
        _riga_pdf(pdf, "Codice Raccolta:", racc["codice"], pw)
        _riga_pdf(pdf, "Data Raccolta:", _fmt_data(racc["data_raccolta"]), pw)
        _riga_pdf(pdf, "Kg Olive Totali:", f"{racc['kg_olive_totali']:.1f} kg", pw)
        _riga_pdf(pdf, "Metodo:", racc["metodo_raccolta"], pw)
        _riga_pdf(pdf, "Maturazione:", racc["maturazione"], pw)

    if parcelle:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        col_w = [pw * 0.15, pw * 0.30, pw * 0.25, pw * 0.15, pw * 0.15]
        headers = ["Codice", "Nome", "Varieta'", "Superficie", "Kg Olive"]
        pdf.set_fill_color(60, 80, 30)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 6, h, border=1, fill=True)
        pdf.ln()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8)
        for p in parcelle:
            pdf.cell(col_w[0], 5, p["codice"], border=1)
            pdf.cell(col_w[1], 5, p["nome"], border=1)
            pdf.cell(col_w[2], 5, p["varieta"], border=1)
            pdf.cell(col_w[3], 5, f"{p['superficie_ettari']:.2f} ha", border=1, align="R")
            pdf.cell(col_w[4], 5, f"{p['kg_olive']:.1f} kg", border=1, align="R")
            pdf.ln()
    pdf.ln(3)

    # --- SEZIONE 3: CONFEZIONAMENTI ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(40, 60, 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(pw, 7, f"  CONFEZIONAMENTI ({len(confs)})", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    if confs:
        pdf.set_font("Helvetica", "B", 9)
        col_w = [pw * 0.10, pw * 0.30, pw * 0.12, pw * 0.12, pw * 0.18, pw * 0.18]
        headers = ["Codice", "Contenitore", "Unita'", "Cap. (L)", "Litri Lotto", "Listino"]
        pdf.set_fill_color(60, 80, 30)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 6, h, border=1, fill=True)
        pdf.ln()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8)
        for c in confs:
            pdf.cell(col_w[0], 5, c["codice"], border=1)
            pdf.cell(col_w[1], 5, c["contenitore"][:30], border=1)
            pdf.cell(col_w[2], 5, str(c["num_unita"]), border=1, align="R")
            pdf.cell(col_w[3], 5, f"{c['capacita_litri']:.2f}", border=1, align="R")
            pdf.cell(col_w[4], 5, f"{c['litri_da_lotto']:.1f} L", border=1, align="R")
            listino = f"EUR {c['prezzo_listino']:.2f}" if c.get("prezzo_listino") else "-"
            pdf.cell(col_w[5], 5, listino, border=1, align="R")
            pdf.ln()
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(pw, 6, "Nessun confezionamento associato.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # --- SEZIONE 4: VENDITE ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(40, 60, 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(pw, 7, f"  VENDITE ({len(vendite)})", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    if vendite:
        pdf.set_font("Helvetica", "B", 9)
        col_w = [pw * 0.15, pw * 0.15, pw * 0.30, pw * 0.10, pw * 0.15, pw * 0.15]
        headers = ["Vendita", "Data", "Cliente", "Unita'", "Importo", "Stato"]
        pdf.set_fill_color(60, 80, 30)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 6, h, border=1, fill=True)
        pdf.ln()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8)
        for v in vendite:
            pdf.cell(col_w[0], 5, v["vendita_codice"], border=1)
            pdf.cell(col_w[1], 5, _fmt_data(v["data_vendita"]), border=1)
            pdf.cell(col_w[2], 5, v["cliente_denominazione"][:28], border=1)
            pdf.cell(col_w[3], 5, str(v["quantita"]), border=1, align="R")
            pdf.cell(col_w[4], 5, f"EUR {v['importo_riga']:.2f}", border=1, align="R")
            pdf.cell(col_w[5], 5, v["stato"], border=1, align="C")
            pdf.ln()
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(pw, 6, "Nessuna vendita associata.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # --- SEZIONE 5: RIEPILOGO ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(40, 60, 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(pw, 7, "  RIEPILOGO", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 9)
    _riga_pdf(pdf, "Litri Olio Prodotti:", f"{riep['litri_olio_totali']:.1f} L", pw)
    _riga_pdf(pdf, "Litri Confezionati:", f"{riep['litri_confezionati']:.1f} L", pw)
    _riga_pdf(pdf, "Litri Disponibili:", f"{riep['litri_disponibili']:.1f} L", pw)
    _riga_pdf(pdf, "Confezionamenti:", str(riep["num_confezionamenti"]), pw)
    _riga_pdf(pdf, "Vendite:", str(riep["num_vendite"]), pw)
    _riga_pdf(pdf, "Unita' Vendute:", str(riep["unita_vendute"]), pw)
    _riga_pdf(pdf, "Fatturato:", f"EUR {riep['fatturato']:.2f}", pw)

    # Output
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def _riga_pdf(pdf, label: str, value: str, pw: float):
    """Stampa una riga label: value."""
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(pw * 0.35, 5, label)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(pw * 0.65, 5, value, new_x="LMARGIN", new_y="NEXT")


def _fmt_data(iso_date: str) -> str:
    """Formatta data ISO in formato italiano GG/MM/AAAA."""
    if not iso_date:
        return "-"
    parts = iso_date.split("-")
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return iso_date
