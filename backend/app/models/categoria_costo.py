from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CategoriaCostoBase(BaseModel):
    codice: str = Field(..., max_length=20)
    nome: str = Field(..., max_length=100)
    tipo_costo: str = Field(..., max_length=15)  # campagna / strutturale
    attiva: bool = True
    ordine: int = 0


class CategoriaCostoCreate(CategoriaCostoBase):
    pass


class CategoriaCostoUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    nome: Optional[str] = Field(None, max_length=100)
    tipo_costo: Optional[str] = Field(None, max_length=15)
    attiva: Optional[bool] = None
    ordine: Optional[int] = None


class CategoriaCostoOut(CategoriaCostoBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
