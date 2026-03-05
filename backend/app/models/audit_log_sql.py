from sqlalchemy import Column, DateTime, Integer, String, Text, func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(50), nullable=False, index=True)
    azione = Column(String(20), nullable=False, index=True)      # creato, modificato, eliminato, confermato, spedito, pagato
    entita = Column(String(30), nullable=False, index=True)      # raccolta, lotto, costo, vendita, ...
    entita_id = Column(Integer, nullable=True)
    codice_entita = Column(String(30), nullable=True)            # R/001/2025, V/002/2025, ...
    dettagli = Column(Text, nullable=True)                       # info aggiuntive
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
