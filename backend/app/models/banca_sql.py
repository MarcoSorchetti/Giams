from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Banca(Base):
    __tablename__ = "banche"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(10), unique=True, nullable=False, index=True)
    denominazione = Column(String(200), nullable=False)
    iban = Column(String(34), nullable=True)
    bic_swift = Column(String(11), nullable=True)
    abi = Column(String(5), nullable=True)
    cab = Column(String(5), nullable=True)
    numero_conto = Column(String(20), nullable=True)
    filiale = Column(String(200), nullable=True)
    intestatario = Column(String(200), nullable=True)
    tipo_conto = Column(String(30), nullable=False, server_default="corrente")
    note = Column(Text, nullable=True)
    attivo = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
