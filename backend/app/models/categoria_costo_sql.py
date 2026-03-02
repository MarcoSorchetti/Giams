from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class CategoriaCosto(Base):
    __tablename__ = "categorie_costo"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(20), unique=True, nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    tipo_costo = Column(String(15), nullable=False)  # campagna / strutturale
    attiva = Column(Boolean, nullable=False, server_default="true")
    ordine = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
