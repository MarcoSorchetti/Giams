"""Utility condivise per denominazione fornitore/cliente."""


def fornitore_denominazione(f):
    """Restituisce la denominazione del fornitore (ragione sociale o nome+cognome)."""
    if not f:
        return None
    if f.tipo_fornitore == "azienda":
        return f.ragione_sociale or ""
    parti = [f.nome or "", f.cognome or ""]
    return " ".join(p for p in parti if p)


def cliente_denominazione(c):
    """Restituisce la denominazione del cliente (ragione sociale o nome+cognome)."""
    if not c:
        return None
    if c.tipo_cliente == "azienda":
        return c.ragione_sociale or ""
    parti = [c.nome or "", c.cognome or ""]
    return " ".join(p for p in parti if p)
