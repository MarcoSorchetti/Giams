from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BancaBase(BaseModel):
    codice: str = Field(..., max_length=10)
    denominazione: str = Field(..., max_length=200)
    iban: Optional[str] = Field(None, max_length=34)
    bic_swift: Optional[str] = Field(None, max_length=11)
    abi: Optional[str] = Field(None, max_length=5)
    cab: Optional[str] = Field(None, max_length=5)
    numero_conto: Optional[str] = Field(None, max_length=20)
    filiale: Optional[str] = Field(None, max_length=200)
    intestatario: Optional[str] = Field(None, max_length=200)
    tipo_conto: str = Field("corrente", max_length=30)
    note: Optional[str] = None
    attivo: bool = True


class BancaCreate(BancaBase):
    pass


class BancaUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=10)
    denominazione: Optional[str] = Field(None, max_length=200)
    iban: Optional[str] = Field(None, max_length=34)
    bic_swift: Optional[str] = Field(None, max_length=11)
    abi: Optional[str] = Field(None, max_length=5)
    cab: Optional[str] = Field(None, max_length=5)
    numero_conto: Optional[str] = Field(None, max_length=20)
    filiale: Optional[str] = Field(None, max_length=200)
    intestatario: Optional[str] = Field(None, max_length=200)
    tipo_conto: Optional[str] = Field(None, max_length=30)
    note: Optional[str] = None
    attivo: Optional[bool] = None


class BancaOut(BancaBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
