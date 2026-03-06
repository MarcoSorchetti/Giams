from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Costo(Base):
    __tablename__ = "costi"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(20), unique=True, nullable=False, index=True)
    categoria_id = Column(Integer, ForeignKey("categorie_costo.id", ondelete="RESTRICT"), nullable=False, index=True)
    anno_campagna = Column(Integer, nullable=False, index=True)
    descrizione = Column(String(200), nullable=False)

    # Fornitore (opzionale)
    fornitore_id = Column(Integer, ForeignKey("fornitori.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Dati fattura
    data_fattura = Column(Date, nullable=False)
    numero_fattura = Column(String(50), nullable=True)
    tipo_documento = Column(String(20), nullable=False, server_default="fattura")

    # Importi
    imponibile = Column(Numeric(12, 3), nullable=False)
    iva_percentuale = Column(Numeric(5, 2), nullable=False, server_default="22")
    importo_iva = Column(Numeric(12, 2), nullable=False, server_default="0")
    importo_totale = Column(Numeric(12, 2), nullable=False)

    # Pagamento
    data_pagamento = Column(Date, nullable=True)
    modalita_pagamento = Column(String(20), nullable=True)
    riferimento_pagamento = Column(String(50), nullable=True)
    stato_pagamento = Column(String(15), nullable=False, server_default="da_pagare")

    # Ammortamento (solo strutturali)
    anni_ammortamento = Column(Integer, nullable=False, server_default="0")

    # Documento allegato (path relativo, es. "costi/C_001_2025_abc12345.pdf")
    documento = Column(String(255), nullable=True)

    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
