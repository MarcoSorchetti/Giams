from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String
from sqlalchemy.sql import func

from app.database import Base


class Contenitore(Base):
    __tablename__ = "contenitori"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(30), unique=True, nullable=False, index=True)
    descrizione = Column(String(100), nullable=False)
    capacita_litri = Column(Numeric(5, 2), nullable=False)
    foto = Column(String(255), nullable=True)
    attivo = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
