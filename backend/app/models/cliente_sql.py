from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Cliente(Base):
    __tablename__ = "clienti"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(20), unique=True, nullable=False, index=True)
    tipo_cliente = Column(String(10), nullable=False)  # privato / azienda

    # Anagrafica privato
    nome = Column(String(50), nullable=True)
    cognome = Column(String(50), nullable=True)
    codice_fiscale = Column(String(16), nullable=True)

    # Anagrafica azienda
    ragione_sociale = Column(String(150), nullable=True)
    partita_iva = Column(String(13), nullable=True)
    codice_sdi = Column(String(7), nullable=True, server_default="0000000")
    pec = Column(String(100), nullable=True)
    referente_nome = Column(String(100), nullable=True)
    referente_telefono = Column(String(20), nullable=True)

    # Indirizzo fatturazione
    indirizzo = Column(String(150), nullable=True)
    cap = Column(String(5), nullable=True)
    citta = Column(String(100), nullable=True)
    provincia = Column(String(2), nullable=True)

    # Indirizzo consegna
    consegna_indirizzo = Column(String(150), nullable=True)
    consegna_cap = Column(String(5), nullable=True)
    consegna_citta = Column(String(100), nullable=True)
    consegna_provincia = Column(String(2), nullable=True)

    # Contatti
    email = Column(String(100), nullable=True)
    telefono = Column(String(20), nullable=True)

    # Commerciale
    sconto_default = Column(Numeric(6, 3), nullable=False, server_default="0")

    attivo = Column(Boolean, nullable=False, server_default="true")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
