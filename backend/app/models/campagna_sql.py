from sqlalchemy import Column, Date, DateTime, Integer, String, Text, func

from app.database import Base


class Campagna(Base):
    __tablename__ = "campagne"

    id = Column(Integer, primary_key=True, index=True)
    anno = Column(Integer, unique=True, nullable=False, index=True)
    # "aperta" | "chiusa"
    stato = Column(String(10), nullable=False, server_default="aperta")
    data_inizio = Column(Date, nullable=True)
    data_fine = Column(Date, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
