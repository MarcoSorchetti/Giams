from typing import Optional
from pydantic import BaseModel, Field
from datetime import date, datetime


class MovimentoMagBase(BaseModel):
    confezionamento_id: int
    tipo_movimento: str = Field(..., max_length=10)
    causale: str = Field(..., max_length=20)
    quantita: int = Field(..., gt=0)
    data_movimento: date
    anno_campagna: int
    cliente_id: Optional[int] = None
    riferimento_documento: Optional[str] = Field(None, max_length=100)
    note: Optional[str] = None


class MovimentoMagCreate(MovimentoMagBase):
    codice: Optional[str] = Field(None, max_length=20)


class MovimentoMagUpdate(BaseModel):
    tipo_movimento: Optional[str] = Field(None, max_length=10)
    causale: Optional[str] = Field(None, max_length=20)
    quantita: Optional[int] = Field(None, gt=0)
    data_movimento: Optional[date] = None
    anno_campagna: Optional[int] = None
    cliente_id: Optional[int] = None
    riferimento_documento: Optional[str] = Field(None, max_length=100)
    note: Optional[str] = None


class MovimentoMagOut(MovimentoMagBase):
    id: int
    codice: str
    confezionamento_codice: Optional[str] = None
    confezionamento_formato: Optional[str] = None
    contenitore_descrizione: Optional[str] = None
    cliente_denominazione: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
