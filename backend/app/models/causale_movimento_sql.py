from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.database import Base


class CausaleMovimento(Base):
    __tablename__ = "causali_movimento"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(30), unique=True, nullable=False, index=True)
    label = Column(String(80), nullable=False)
    # "carico" | "scarico"
    tipo_movimento = Column(String(10), nullable=False)
    # True = protetta (vendita, produzione) — non eliminabile, codice non modificabile
    sistema = Column(Boolean, nullable=False, server_default="false")
    attivo = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
