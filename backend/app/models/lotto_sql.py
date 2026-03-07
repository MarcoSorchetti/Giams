from sqlalchemy import Column, DateTime, Date, ForeignKey, Integer, Numeric, String, Text, func
from app.database import Base


class LottoOlio(Base):
    __tablename__ = "lotti_olio"

    id = Column(Integer, primary_key=True, index=True)
    codice_lotto = Column(String(30), unique=True, nullable=False, index=True)
    raccolta_id = Column(Integer, ForeignKey("raccolte.id", ondelete="CASCADE"), nullable=False, unique=True)
    anno_campagna = Column(Integer, nullable=False, index=True)
    data_molitura = Column(Date, nullable=False)
    frantoio = Column(String(100), nullable=False)
    frantoio_id = Column(Integer, ForeignKey("frantoi.id"), nullable=True)
    kg_olive = Column(Numeric(8, 2), nullable=False)
    litri_olio = Column(Numeric(8, 2), nullable=False)
    kg_olio = Column(Numeric(8, 2), nullable=True)
    resa_percentuale = Column(Numeric(5, 2), nullable=True)
    acidita = Column(Numeric(4, 2), nullable=True)
    perossidi = Column(Numeric(5, 1), nullable=True)
    polifenoli = Column(Integer, nullable=True)
    tipo_olio = Column(String(30), nullable=False)
    certificazione = Column(String(50), nullable=True)
    costo_frantoio = Column(Numeric(8, 2), nullable=True)
    costo_trasporto = Column(Numeric(8, 2), nullable=True)
    costo_totale_molitura = Column(Numeric(8, 2), nullable=True)
    stato = Column(String(20), nullable=False, server_default="disponibile")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
