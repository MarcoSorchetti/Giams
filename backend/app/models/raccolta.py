from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date, datetime


class RaccoltaParcellaBase(BaseModel):
    parcella_id: int
    kg_olive: float


class RaccoltaParcellaOut(RaccoltaParcellaBase):
    id: int
    parcella_codice: Optional[str] = None
    parcella_nome: Optional[str] = None

    model_config = {"from_attributes": True}


class RaccoltaBase(BaseModel):
    codice: str = Field(..., max_length=20)
    data_raccolta: date
    anno_campagna: int
    kg_olive_totali: float
    metodo_raccolta: str = Field(..., max_length=30)
    maturazione: str = Field(..., max_length=20)
    num_operai: Optional[int] = None
    ore_lavoro: Optional[float] = None
    costo_manodopera: Optional[float] = None
    costo_noleggio: Optional[float] = None
    costo_totale_raccolta: Optional[float] = None
    note: Optional[str] = None


class RaccoltaCreate(RaccoltaBase):
    parcelle: List[RaccoltaParcellaBase] = []


class RaccoltaUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    data_raccolta: Optional[date] = None
    anno_campagna: Optional[int] = None
    kg_olive_totali: Optional[float] = None
    metodo_raccolta: Optional[str] = Field(None, max_length=30)
    maturazione: Optional[str] = Field(None, max_length=20)
    num_operai: Optional[int] = None
    ore_lavoro: Optional[float] = None
    costo_manodopera: Optional[float] = None
    costo_noleggio: Optional[float] = None
    costo_totale_raccolta: Optional[float] = None
    note: Optional[str] = None
    parcelle: Optional[List[RaccoltaParcellaBase]] = None


class RaccoltaOut(RaccoltaBase):
    id: int
    parcelle: List[RaccoltaParcellaOut] = []
    ha_lotto: bool = False
    lotto_litri: Optional[float] = None
    lotto_kg_olio: Optional[float] = None
    lotto_resa: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
