from sqlalchemy import Column, DateTime, Date, ForeignKey, Integer, Numeric, String, Text, func
from app.database import Base


class Raccolta(Base):
    __tablename__ = "raccolte"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(20), unique=True, nullable=False, index=True)
    data_raccolta = Column(Date, nullable=False)
    anno_campagna = Column(Integer, nullable=False)
    kg_olive_totali = Column(Numeric(8, 2), nullable=False)
    metodo_raccolta = Column(String(30), nullable=False)
    maturazione = Column(String(20), nullable=False)
    num_operai = Column(Integer, nullable=True)
    ore_lavoro = Column(Numeric(5, 1), nullable=True)
    costo_manodopera = Column(Numeric(8, 2), nullable=True)
    costo_noleggio = Column(Numeric(8, 2), nullable=True)
    costo_totale_raccolta = Column(Numeric(8, 2), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())


class RaccoltaParcella(Base):
    __tablename__ = "raccolta_parcelle"

    id = Column(Integer, primary_key=True, index=True)
    raccolta_id = Column(Integer, ForeignKey("raccolte.id", ondelete="CASCADE"), nullable=False)
    parcella_id = Column(Integer, ForeignKey("parcelle.id"), nullable=False)
    kg_olive = Column(Numeric(8, 2), nullable=False)
