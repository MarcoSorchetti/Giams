from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FrantoioBase(BaseModel):
    codice: str = Field(..., max_length=10)
    denominazione: str = Field(..., max_length=200)
    partita_iva: Optional[str] = Field(None, max_length=16)
    indirizzo: Optional[str] = Field(None, max_length=200)
    cap: Optional[str] = Field(None, max_length=5)
    citta: Optional[str] = Field(None, max_length=100)
    provincia: Optional[str] = Field(None, max_length=2)
    telefono: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    referente: Optional[str] = Field(None, max_length=100)
    servizi: str = Field("molitura", max_length=50)
    note: Optional[str] = None
    attivo: bool = True


class FrantoioCreate(FrantoioBase):
    pass


class FrantoioUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=10)
    denominazione: Optional[str] = Field(None, max_length=200)
    partita_iva: Optional[str] = Field(None, max_length=16)
    indirizzo: Optional[str] = Field(None, max_length=200)
    cap: Optional[str] = Field(None, max_length=5)
    citta: Optional[str] = Field(None, max_length=100)
    provincia: Optional[str] = Field(None, max_length=2)
    telefono: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    referente: Optional[str] = Field(None, max_length=100)
    servizi: Optional[str] = Field(None, max_length=50)
    note: Optional[str] = None
    attivo: Optional[bool] = None


class FrantoioOut(FrantoioBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
