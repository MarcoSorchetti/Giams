from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func,
)
from app.database import Base


class Vendita(Base):
    __tablename__ = "vendite"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(20), unique=True, nullable=False, index=True)

    cliente_id = Column(Integer, ForeignKey("clienti.id", ondelete="RESTRICT"), nullable=False, index=True)
    data_vendita = Column(Date, nullable=False, index=True)
    anno_campagna = Column(Integer, nullable=False, index=True)

    # Stato: bozza | confermata | spedita | pagata
    stato = Column(String(15), nullable=False, server_default="bozza")

    # Finanziari
    imponibile = Column(Numeric(12, 2), nullable=False, server_default="0")
    sconto_percentuale = Column(Numeric(5, 2), nullable=True)
    imponibile_scontato = Column(Numeric(12, 2), nullable=False, server_default="0")
    iva_percentuale = Column(Numeric(5, 2), nullable=False, server_default="4")
    importo_iva = Column(Numeric(12, 2), nullable=False, server_default="0")
    arrotondamento = Column(Numeric(10, 2), nullable=False, server_default="0")
    importo_totale = Column(Numeric(12, 2), nullable=False, server_default="0")

    # Fattura interna (generata alla conferma)
    numero_fattura = Column(String(20), nullable=True, unique=True)

    # Pagamento
    data_pagamento = Column(Date, nullable=True)
    modalita_pagamento = Column(String(50), nullable=True)
    riferimento_pagamento = Column(String(100), nullable=True)

    # Spedizione
    data_spedizione = Column(Date, nullable=True)
    numero_ddt = Column(String(20), nullable=True)
    note_spedizione = Column(Text, nullable=True)
    spedizione_indirizzo = Column(String(150), nullable=True)
    spedizione_cap = Column(String(5), nullable=True)
    spedizione_citta = Column(String(100), nullable=True)
    spedizione_provincia = Column(String(2), nullable=True)

    data_conferma = Column(Date, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())


class VenditaRiga(Base):
    __tablename__ = "vendita_righe"

    id = Column(Integer, primary_key=True, index=True)
    vendita_id = Column(Integer, ForeignKey("vendite.id", ondelete="CASCADE"), nullable=False, index=True)
    confezionamento_id = Column(Integer, ForeignKey("confezionamenti.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantita = Column(Integer, nullable=False)
    prezzo_listino = Column(Numeric(10, 2), nullable=True)
    sconto_percentuale = Column(Numeric(6, 3), nullable=False, server_default="0")
    prezzo_unitario = Column(Numeric(10, 2), nullable=False)
    importo_riga = Column(Numeric(12, 2), nullable=False)
