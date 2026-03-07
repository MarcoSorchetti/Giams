from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Azienda(Base):
    __tablename__ = "azienda"

    id = Column(Integer, primary_key=True, index=True)
    ragione_sociale = Column(String(200), nullable=False)
    forma_giuridica = Column(String(30), nullable=True)
    partita_iva = Column(String(16), nullable=True)
    codice_fiscale = Column(String(16), nullable=True)
    rea = Column(String(30), nullable=True)
    codice_ateco = Column(String(10), nullable=True)
    pec = Column(String(100), nullable=True)
    codice_sdi = Column(String(7), nullable=True)
    # Sede legale
    sede_legale_indirizzo = Column(String(200), nullable=True)
    sede_legale_cap = Column(String(5), nullable=True)
    sede_legale_citta = Column(String(100), nullable=True)
    sede_legale_provincia = Column(String(2), nullable=True)
    # Sede operativa
    sede_operativa_indirizzo = Column(String(200), nullable=True)
    sede_operativa_cap = Column(String(5), nullable=True)
    sede_operativa_citta = Column(String(100), nullable=True)
    sede_operativa_provincia = Column(String(2), nullable=True)
    # Contatti
    telefono = Column(String(20), nullable=True)
    cellulare = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    sito_web = Column(String(200), nullable=True)
    # Altro
    banca_id = Column(Integer, nullable=True)
    logo_path = Column(String(200), nullable=True)
    rappresentante_legale = Column(String(200), nullable=True)
    capitale_sociale = Column(Numeric(12, 2), nullable=True)
    note = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
