from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, func
from app.database import Base


class Parcella(Base):
    __tablename__ = "parcelle"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(20), unique=True, nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    superficie_ettari = Column(Numeric(6, 2), nullable=False)
    varieta_principale = Column(String(100), nullable=False)
    varieta_secondaria = Column(String(100), nullable=True)
    num_piante = Column(Integer, nullable=False)
    anno_impianto = Column(Integer, nullable=True)
    sistema_irrigazione = Column(String(50), nullable=True)
    tipo_terreno = Column(String(50), nullable=True)
    esposizione = Column(String(20), nullable=True)
    altitudine_m = Column(Integer, nullable=True)
    stato = Column(String(20), nullable=False, server_default="produttivo")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
