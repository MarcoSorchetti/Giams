"""
Generazione PDF per fattura interna e DDT - GIAMS Vendite
"""
import io
import os
from fpdf import FPDF
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Dati azienda (intestazione documenti) — fallback se DB vuoto
# ---------------------------------------------------------------------------
_AZIENDA_DEFAULT = {
    "nome": "Gia.Mar Green Farm Srl",
    "indirizzo": "",
    "cap": "",
    "citta": "",
    "provincia": "",
    "partita_iva": "",
    "telefono": "",
    "email": "",
}

LOGO_PATH = os.path.join(os.path.dirname(__file__), "../../../frontend/assets/LogoGiaMarHome.png")


def get_azienda_data(db: Session) -> dict:
    """Legge i dati aziendali dal DB. Fallback a valori default se vuoto."""
    from app.models.azienda_sql import Azienda
    az = db.query(Azienda).first()
    if not az:
        return _AZIENDA_DEFAULT.copy()
    forma = f" {az.forma_giuridica}" if az.forma_giuridica else ""
    return {
        "nome": f"{az.ragione_sociale or ''}{forma}",
        "indirizzo": az.sede_legale_indirizzo or "",
        "cap": az.sede_legale_cap or "",
        "citta": az.sede_legale_citta or "",
        "provincia": az.sede_legale_provincia or "",
        "partita_iva": az.partita_iva or "",
        "telefono": az.telefono or "",
        "email": az.pec or az.email or "",
    }


class DocumentoPDF(FPDF):
    """PDF base con intestazione aziendale e piede pagina."""

    def __init__(self, titolo_doc: str = "", azienda: dict = None):
        super().__init__()
        self.titolo_doc = titolo_doc
        self.azienda = azienda or _AZIENDA_DEFAULT

    def header(self):
        az = self.azienda
        # Logo
        if os.path.isfile(LOGO_PATH):
            self.image(LOGO_PATH, 10, 8, 30)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, az["nome"], new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 8)
        # Indirizzo (mostra solo se compilato)
        parti_ind = []
        if az["indirizzo"]:
            parti_ind.append(az["indirizzo"])
        loc = ""
        if az["cap"] or az["citta"]:
            loc = f"{az['cap']} {az['citta']}".strip()
            if az["provincia"]:
                loc += f" ({az['provincia']})"
        if loc:
            parti_ind.append(loc)
        if parti_ind:
            self.cell(0, 4, " - ".join(parti_ind), new_x="LMARGIN", new_y="NEXT", align="C")
        # P.IVA, Tel, Email (mostra solo campi compilati)
        dettagli = []
        if az["partita_iva"]:
            dettagli.append(f"P.IVA: {az['partita_iva']}")
        if az["telefono"]:
            dettagli.append(f"Tel: {az['telefono']}")
        if az["email"]:
            dettagli.append(az["email"])
        if dettagli:
            self.cell(0, 4, "  |  ".join(dettagli), new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)
        # Titolo documento
        if self.titolo_doc:
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 8, self.titolo_doc, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)
        # Linea separatrice
        self.set_draw_color(100, 100, 100)
        page_w = self.w - self.r_margin
        self.line(10, self.get_y(), page_w, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.cell(0, 5, f"Documento generato da GIAMS - {self.azienda['nome']}", align="C")
        self.set_y(-10)
        self.cell(0, 5, f"Pagina {self.page_no()}/{{nb}}", align="C")


def _denominazione_cliente(cli):
    if not cli:
        return "Cliente sconosciuto"
    if cli.tipo_cliente == "azienda":
        return cli.ragione_sociale or ""
    parti = [cli.nome or "", cli.cognome or ""]
    return " ".join(p for p in parti if p)


def _indirizzo_cliente(cli):
    if not cli:
        return ""
    parti = []
    if cli.indirizzo:
        parti.append(cli.indirizzo)
    loc = []
    if cli.cap:
        loc.append(cli.cap)
    if cli.citta:
        loc.append(cli.citta)
    if cli.provincia:
        loc.append(f"({cli.provincia})")
    if loc:
        parti.append(" ".join(loc))
    return " - ".join(parti)


def _fmt(val, decimali=2):
    """Formatta un numero con separatore migliaia e decimali."""
    if val is None:
        return "-"
    return f"{float(val):,.{decimali}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# Fattura interna
# ---------------------------------------------------------------------------

def genera_fattura_pdf(vendita, cliente, righe_info: list, db: Session = None) -> bytes:
    """Genera PDF fattura interna. Restituisce bytes del PDF."""
    az = get_azienda_data(db) if db else _AZIENDA_DEFAULT
    titolo = f"FATTURA INTERNA N. {vendita.numero_fattura or vendita.codice}"
    pdf = DocumentoPDF(titolo_doc=titolo, azienda=az)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Dati documento
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(95, 5, f"Data: {vendita.data_vendita.strftime('%d/%m/%Y') if vendita.data_vendita else '-'}", new_x="RIGHT")
    pdf.cell(95, 5, f"Cod. Vendita: {vendita.codice}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Dati cliente
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "CLIENTE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, _denominazione_cliente(cliente), new_x="LMARGIN", new_y="NEXT")
    if cliente:
        pdf.cell(0, 5, _indirizzo_cliente(cliente), new_x="LMARGIN", new_y="NEXT")
        if cliente.partita_iva:
            pdf.cell(0, 5, f"P.IVA: {cliente.partita_iva}", new_x="LMARGIN", new_y="NEXT")
        if cliente.codice_fiscale:
            pdf.cell(0, 5, f"C.F.: {cliente.codice_fiscale}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Tabella righe
    pdf.set_font("Helvetica", "B", 8)
    col_w = [10, 25, 45, 35, 20, 25, 30]
    headers = ["#", "Codice", "Prodotto", "Contenitore", "Qty", "Prezzo Unit.", "Importo"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for idx, r in enumerate(righe_info, 1):
        pdf.cell(col_w[0], 6, str(idx), border=1, align="C")
        pdf.cell(col_w[1], 6, r["confezionamento_codice"], border=1)
        pdf.cell(col_w[2], 6, r["confezionamento_formato"], border=1)
        pdf.cell(col_w[3], 6, r["contenitore_descrizione"], border=1)
        pdf.cell(col_w[4], 6, str(r["quantita"]), border=1, align="C")
        pdf.cell(col_w[5], 6, _fmt(r["prezzo_unitario"]), border=1, align="R")
        pdf.cell(col_w[6], 6, _fmt(r["importo_riga"]), border=1, align="R")
        pdf.ln()

    pdf.ln(5)

    # Totali
    x_label = 120
    x_val = 160
    w_val = 30

    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(x_label)
    pdf.cell(40, 6, "Imponibile:", align="R")
    pdf.cell(w_val, 6, f"EUR {_fmt(vendita.imponibile)}", align="R")
    pdf.ln()

    if vendita.sconto_percentuale and float(vendita.sconto_percentuale) > 0:
        pdf.set_x(x_label)
        pdf.cell(40, 6, f"Sconto ({_fmt(vendita.sconto_percentuale, 1)}%):", align="R")
        sconto_val = float(vendita.imponibile) - float(vendita.imponibile_scontato)
        pdf.cell(w_val, 6, f"- EUR {_fmt(sconto_val)}", align="R")
        pdf.ln()
        pdf.set_x(x_label)
        pdf.cell(40, 6, "Imponibile scontato:", align="R")
        pdf.cell(w_val, 6, f"EUR {_fmt(vendita.imponibile_scontato)}", align="R")
        pdf.ln()

    pdf.set_x(x_label)
    pdf.cell(40, 6, f"IVA ({_fmt(vendita.iva_percentuale, 0)}%):", align="R")
    pdf.cell(w_val, 6, f"EUR {_fmt(vendita.importo_iva)}", align="R")
    pdf.ln()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_x(x_label)
    pdf.cell(40, 8, "TOTALE:", align="R")
    pdf.cell(w_val, 8, f"EUR {_fmt(vendita.importo_totale)}", align="R")
    pdf.ln()

    # Note
    if vendita.note:
        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4, f"Note: {vendita.note}")

    # Stato pagamento
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 8)
    if vendita.data_pagamento:
        pdf.cell(0, 5, f"Pagamento ricevuto il {vendita.data_pagamento.strftime('%d/%m/%Y')} - {vendita.modalita_pagamento or ''}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 5, "Pagamento: DA SALDARE", new_x="LMARGIN", new_y="NEXT")

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# DDT - Documento di Trasporto
# ---------------------------------------------------------------------------

def genera_ddt_pdf(vendita, cliente, righe_info: list, db: Session = None) -> bytes:
    """Genera PDF DDT. Restituisce bytes del PDF."""
    az = get_azienda_data(db) if db else _AZIENDA_DEFAULT
    titolo = f"DOCUMENTO DI TRASPORTO N. {vendita.numero_ddt or vendita.codice}"
    pdf = DocumentoPDF(titolo_doc=titolo, azienda=az)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Dati documento
    pdf.set_font("Helvetica", "", 9)
    data_sped = vendita.data_spedizione.strftime('%d/%m/%Y') if vendita.data_spedizione else vendita.data_vendita.strftime('%d/%m/%Y')
    pdf.cell(95, 5, f"Data: {data_sped}", new_x="RIGHT")
    pdf.cell(95, 5, f"Cod. Vendita: {vendita.codice}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Destinatario
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "DESTINATARIO", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, _denominazione_cliente(cliente), new_x="LMARGIN", new_y="NEXT")

    # Indirizzo spedizione
    sped_parti = []
    if vendita.spedizione_indirizzo:
        sped_parti.append(vendita.spedizione_indirizzo)
    loc = []
    if vendita.spedizione_cap:
        loc.append(vendita.spedizione_cap)
    if vendita.spedizione_citta:
        loc.append(vendita.spedizione_citta)
    if vendita.spedizione_provincia:
        loc.append(f"({vendita.spedizione_provincia})")
    if loc:
        sped_parti.append(" ".join(loc))
    if sped_parti:
        pdf.cell(0, 5, " - ".join(sped_parti), new_x="LMARGIN", new_y="NEXT")
    elif cliente:
        pdf.cell(0, 5, _indirizzo_cliente(cliente), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # Tabella righe (senza prezzi)
    pdf.set_font("Helvetica", "B", 8)
    col_w = [15, 35, 55, 50, 35]
    headers = ["#", "Codice", "Prodotto", "Contenitore", "Quantita'"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for idx, r in enumerate(righe_info, 1):
        pdf.cell(col_w[0], 6, str(idx), border=1, align="C")
        pdf.cell(col_w[1], 6, r["confezionamento_codice"], border=1)
        pdf.cell(col_w[2], 6, r["confezionamento_formato"], border=1)
        pdf.cell(col_w[3], 6, r["contenitore_descrizione"], border=1)
        pdf.cell(col_w[4], 6, str(r["quantita"]), border=1, align="C")
        pdf.ln()

    # Note spedizione
    if vendita.note_spedizione:
        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4, f"Note: {vendita.note_spedizione}")

    # Firme
    pdf.ln(15)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(95, 5, "Firma mittente:", border="B")
    pdf.cell(95, 5, "Firma destinatario:", border="B")
    pdf.ln(15)
    pdf.cell(95, 5, "_______________________________")
    pdf.cell(95, 5, "_______________________________")

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
