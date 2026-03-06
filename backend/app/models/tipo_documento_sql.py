from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.database import Base


class TipoDocumento(Base):
    __tablename__ = "tipi_documento"

    id = Column(Integer, primary_key=True, index=True)
    valore = Column(String(30), unique=True, nullable=False, index=True)
    etichetta = Column(String(80), nullable=False)
    # True = protetta — non eliminabile
    sistema = Column(Boolean, nullable=False, server_default="false")
    attivo = Column(Boolean, nullable=False, server_default="true")
    ordine = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
