"""
Generazione PDF Listino Prezzi per campagna - GIAMS
"""
import io
import os
from datetime import date
from fpdf import FPDF


# ---------------------------------------------------------------------------
# Dati azienda (stessi di pdf_vendita)
# ---------------------------------------------------------------------------
AZIENDA = {
    "nome": "Gia.Mar Green Farm Srl",
    "indirizzo": "Via delle Olive, 1",
    "cap": "00100",
    "citta": "Roma",
    "provincia": "RM",
    "partita_iva": "IT12345678901",
    "telefono": "+39 06 1234567",
    "email": "info@giamarsrl.it",
}

LOGO_PATH = os.path.join(os.path.dirname(__file__), "../../../frontend/assets/LogoGiaMarHome.png")

# Colori brand
VERDE_SCURO = (34, 87, 46)
VERDE_CHIARO = (76, 148, 68)
GRIGIO_CHIARO = (245, 245, 245)
BIANCO = (255, 255, 255)
NERO = (33, 33, 33)


def _fmt(val, decimali=2):
    """Formatta un numero con separatore migliaia e decimali."""
    if val is None:
        return "-"
    return f"{float(val):,.{decimali}f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ListinoPDF(FPDF):
    """PDF listino prezzi con design accattivante."""

    def __init__(self, anno_campagna: int, campagna_info: dict = None):
        super().__init__()
        self.anno_campagna = anno_campagna
        self.campagna_info = campagna_info or {}

    def header(self):
        # Banda verde in alto
        self.set_fill_color(*VERDE_SCURO)
        self.rect(0, 0, 210, 50, "F")

        # Logo
        if os.path.isfile(LOGO_PATH):
            self.image(LOGO_PATH, 12, 5, 28)

        # Nome azienda
        self.set_text_color(*BIANCO)
        self.set_font("Helvetica", "B", 20)
        self.set_xy(45, 6)
        self.cell(0, 10, AZIENDA["nome"])

        # Indirizzo e contatti
        self.set_font("Helvetica", "", 8)
        self.set_xy(45, 16)
        self.cell(0, 4, f"{AZIENDA['indirizzo']} - {AZIENDA['cap']} {AZIENDA['citta']} ({AZIENDA['provincia']})")
        self.set_xy(45, 20)
        self.cell(0, 4, f"P.IVA: {AZIENDA['partita_iva']}  |  Tel: {AZIENDA['telefono']}  |  {AZIENDA['email']}")

        # Titolo listino
        self.set_font("Helvetica", "B", 14)
        self.set_xy(45, 28)
        campagna_label = f"{self.anno_campagna}/{self.anno_campagna + 1}"
        self.cell(0, 8, f"LISTINO PREZZI - Campagna Olearia {campagna_label}")

        # Info campagna (date e stato)
        self.set_font("Helvetica", "", 8)
        self.set_xy(45, 37)
        info_parts = []
        di = self.campagna_info.get("data_inizio")
        df = self.campagna_info.get("data_fine")
        if di:
            info_parts.append(f"Inizio: {di}")
        if df:
            info_parts.append(f"Fine: {df}")
        stato = self.campagna_info.get("stato", "")
        if stato:
            info_parts.append(f"Stato: {stato.capitalize()}")
        if info_parts:
            self.cell(0, 4, "  |  ".join(info_parts))

        # Reset colore testo
        self.set_text_color(*NERO)
        self.set_y(55)

    def footer(self):
        self.set_y(-20)
        # Linea verde
        self.set_draw_color(*VERDE_SCURO)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(120, 120, 120)
        campagna_label = f"{self.anno_campagna}/{self.anno_campagna + 1}"
        self.cell(0, 4, f"Listino valido per la campagna olearia {campagna_label} - Prezzi IVA inclusa", align="C")
        self.ln(4)
        self.cell(0, 4, f"{AZIENDA['nome']} - Generato il {date.today().strftime('%d/%m/%Y')}  |  Pagina {self.page_no()}/{{nb}}", align="C")


def genera_listino_pdf(anno_campagna: int, prodotti: list, campagna_info: dict = None) -> bytes:
    """
    Genera il PDF del listino prezzi.

    prodotti: lista di dict con chiavi:
        codice, formato, contenitore, capacita_litri,
        prezzo_listino, prezzo_imponibile, iva_percentuale, importo_iva
    campagna_info: dict opzionale con data_inizio, data_fine, stato
    """
    pdf = ListinoPDF(anno_campagna=anno_campagna, campagna_info=campagna_info)
    pdf.alias_nb_pages()
    pdf.add_page()

    if not prodotti:
        pdf.set_font("Helvetica", "", 12)
        pdf.ln(20)
        pdf.cell(0, 10, "Nessun prodotto disponibile per questa campagna.", align="C")
        buf = io.BytesIO()
        pdf.output(buf)
        return buf.getvalue()

    # Introduzione
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(2)
    campagna_label = f"{anno_campagna}/{anno_campagna + 1}"
    pdf.multi_cell(0, 5, (
        f"Di seguito il listino prezzi dei nostri prodotti per la campagna olearia {campagna_label}. "
        "Tutti i prezzi sono espressi in Euro. Il prezzo di listino e' comprensivo di IVA."
    ))
    pdf.ln(5)

    # Intestazione tabella (7 colonne)
    col_w = [42, 35, 20, 30, 25, 15, 23]
    headers = ["Prodotto", "Contenitore", "Capacita'", "Prezzo Listino", "Imponibile", "IVA %", "Importo IVA"]

    pdf.set_fill_color(*VERDE_SCURO)
    pdf.set_text_color(*BIANCO)
    pdf.set_font("Helvetica", "B", 8)
    for i, h in enumerate(headers):
        align = "C" if i in (2, 5) else ("R" if i >= 3 else "L")
        pdf.cell(col_w[i], 8, h, border=0, align=align, fill=True)
    pdf.ln()

    # Righe prodotti
    pdf.set_text_color(*NERO)
    pdf.set_font("Helvetica", "", 8)

    for idx, p in enumerate(prodotti):
        # Colore alternato
        if idx % 2 == 0:
            pdf.set_fill_color(*GRIGIO_CHIARO)
        else:
            pdf.set_fill_color(*BIANCO)

        fill = True
        formato_label = p.get("formato", "")
        contenitore_label = p.get("contenitore", "-")
        capacita = f'{_fmt(p.get("capacita_litri", 0), 2)} L'
        prezzo = f'EUR {_fmt(p.get("prezzo_listino", 0))}' if p.get("prezzo_listino") else "-"
        imponibile = f'EUR {_fmt(p.get("prezzo_imponibile", 0))}' if p.get("prezzo_imponibile") else "-"
        iva_pct = f'{_fmt(p.get("iva_percentuale", 4), 0)}%'
        iva_importo = f'EUR {_fmt(p.get("importo_iva", 0))}' if p.get("importo_iva") else "-"

        pdf.cell(col_w[0], 7, formato_label, border=0, fill=fill)
        pdf.cell(col_w[1], 7, contenitore_label, border=0, fill=fill)
        pdf.cell(col_w[2], 7, capacita, border=0, align="C", fill=fill)

        # Prezzo in grassetto
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_w[3], 7, prezzo, border=0, align="R", fill=fill)
        pdf.set_font("Helvetica", "", 8)

        pdf.cell(col_w[4], 7, imponibile, border=0, align="R", fill=fill)
        pdf.cell(col_w[5], 7, iva_pct, border=0, align="C", fill=fill)
        pdf.cell(col_w[6], 7, iva_importo, border=0, align="R", fill=fill)
        pdf.ln()

    # Linea chiusura tabella
    pdf.set_draw_color(*VERDE_SCURO)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    # Note finali
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 4, (
        "Note:\n"
        "- Prezzi franco azienda, trasporto escluso.\n"
        "- Per ordini superiori a 50 unita' contattare per condizioni dedicate.\n"
        "- Disponibilita' soggetta a esaurimento scorte."
    ))

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
