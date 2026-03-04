from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class MovimentoMagazzino(Base):
    __tablename__ = "movimenti_magazzino"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(20), unique=True, nullable=False, index=True)

    # Riferimento al confezionamento (prodotto confezionato)
    confezionamento_id = Column(Integer, ForeignKey("confezionamenti.id"), nullable=False, index=True)

    # Tipo: carico | scarico
    tipo_movimento = Column(String(10), nullable=False)

    # Causale: produzione | omaggio | pubblicita | scarto | vendita
    causale = Column(String(20), nullable=False)

    # Quantita (sempre positivo, il tipo_movimento indica la direzione)
    quantita = Column(Integer, nullable=False)

    data_movimento = Column(Date, nullable=False, index=True)
    anno_campagna = Column(Integer, nullable=False, index=True)

    # Cliente (opzionale, per omaggi o scarichi legati a un cliente)
    cliente_id = Column(Integer, ForeignKey("clienti.id"), nullable=True, index=True)

    # Riferimento documento esterno (fattura, DDT, ecc. — per collegamento futuro con Vendite)
    riferimento_documento = Column(String(100), nullable=True)

    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
