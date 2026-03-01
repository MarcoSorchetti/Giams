from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ParcellaBase(BaseModel):
    codice: str = Field(..., max_length=20)
    nome: str = Field(..., max_length=100)
    superficie_ettari: float
    varieta_principale: str = Field(..., max_length=100)
    varieta_secondaria: Optional[str] = Field(None, max_length=100)
    num_piante: int
    anno_impianto: Optional[int] = None
    sistema_irrigazione: Optional[str] = Field(None, max_length=50)
    tipo_terreno: Optional[str] = Field(None, max_length=50)
    esposizione: Optional[str] = Field(None, max_length=20)
    altitudine_m: Optional[int] = None
    stato: str = Field("produttivo", max_length=20)
    note: Optional[str] = None


class ParcellaCreate(ParcellaBase):
    pass


class ParcellaUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    nome: Optional[str] = Field(None, max_length=100)
    superficie_ettari: Optional[float] = None
    varieta_principale: Optional[str] = Field(None, max_length=100)
    varieta_secondaria: Optional[str] = Field(None, max_length=100)
    num_piante: Optional[int] = None
    anno_impianto: Optional[int] = None
    sistema_irrigazione: Optional[str] = Field(None, max_length=50)
    tipo_terreno: Optional[str] = Field(None, max_length=50)
    esposizione: Optional[str] = Field(None, max_length=20)
    altitudine_m: Optional[int] = None
    stato: Optional[str] = Field(None, max_length=20)
    note: Optional[str] = None


class ParcellaOut(ParcellaBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
