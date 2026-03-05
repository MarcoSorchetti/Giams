from sqlalchemy import Column, DateTime, Date, ForeignKey, Integer, Numeric, String, Text, func
from app.database import Base


class Confezionamento(Base):
    __tablename__ = "confezionamenti"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(20), unique=True, nullable=False, index=True)
    data_confezionamento = Column(Date, nullable=False)
    anno_campagna = Column(Integer, nullable=False, index=True)
    contenitore_id = Column(Integer, ForeignKey("contenitori.id", ondelete="SET NULL"), nullable=True)
    formato = Column(String(30), nullable=False)
    capacita_litri = Column(Numeric(5, 2), nullable=False)
    num_unita = Column(Integer, nullable=False)
    litri_totali = Column(Numeric(8, 2), nullable=False)
    prezzo_imponibile = Column(Numeric(10, 2), nullable=True)
    iva_percentuale = Column(Numeric(5, 2), nullable=False, server_default="4")
    importo_iva = Column(Numeric(10, 2), nullable=True)
    prezzo_listino = Column(Numeric(10, 2), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())


class ConfezionamentoLotto(Base):
    __tablename__ = "confezionamento_lotti"

    id = Column(Integer, primary_key=True, index=True)
    confezionamento_id = Column(Integer, ForeignKey("confezionamenti.id", ondelete="CASCADE"), nullable=False, index=True)
    lotto_id = Column(Integer, ForeignKey("lotti_olio.id", ondelete="CASCADE"), nullable=False, index=True)
    litri_utilizzati = Column(Numeric(8, 2), nullable=False)
