from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Frantoio(Base):
    __tablename__ = "frantoi"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(10), unique=True, nullable=False, index=True)
    denominazione = Column(String(200), nullable=False)
    partita_iva = Column(String(16), nullable=True)
    indirizzo = Column(String(200), nullable=True)
    cap = Column(String(5), nullable=True)
    citta = Column(String(100), nullable=True)
    provincia = Column(String(2), nullable=True)
    telefono = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    referente = Column(String(100), nullable=True)
    servizi = Column(String(50), nullable=False, server_default="molitura")
    note = Column(Text, nullable=True)
    attivo = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
