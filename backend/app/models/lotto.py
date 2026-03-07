from typing import Optional
from pydantic import BaseModel, Field
from datetime import date, datetime


class LottoBase(BaseModel):
    codice_lotto: Optional[str] = Field(None, max_length=30)
    raccolta_id: int
    anno_campagna: int
    data_molitura: date
    frantoio: str = Field(..., max_length=100)
    frantoio_id: Optional[int] = None
    kg_olive: float
    litri_olio: float
    kg_olio: Optional[float] = None
    resa_percentuale: Optional[float] = None
    acidita: Optional[float] = None
    perossidi: Optional[float] = None
    polifenoli: Optional[int] = None
    tipo_olio: str = Field(..., max_length=30)
    certificazione: Optional[str] = Field(None, max_length=50)
    costo_frantoio: Optional[float] = None
    costo_trasporto: Optional[float] = None
    costo_totale_molitura: Optional[float] = None
    stato: str = Field("disponibile", max_length=20)
    note: Optional[str] = None


class LottoCreate(LottoBase):
    pass


class LottoUpdate(BaseModel):
    codice_lotto: Optional[str] = Field(None, max_length=30)
    anno_campagna: Optional[int] = None
    data_molitura: Optional[date] = None
    frantoio: Optional[str] = Field(None, max_length=100)
    frantoio_id: Optional[int] = None
    kg_olive: Optional[float] = None
    litri_olio: Optional[float] = None
    kg_olio: Optional[float] = None
    resa_percentuale: Optional[float] = None
    acidita: Optional[float] = None
    perossidi: Optional[float] = None
    polifenoli: Optional[int] = None
    tipo_olio: Optional[str] = Field(None, max_length=30)
    certificazione: Optional[str] = Field(None, max_length=50)
    costo_frantoio: Optional[float] = None
    costo_trasporto: Optional[float] = None
    costo_totale_molitura: Optional[float] = None
    stato: Optional[str] = Field(None, max_length=20)
    note: Optional[str] = None


class LottoOut(LottoBase):
    id: int
    raccolta_codice: Optional[str] = None
    frantoio_denominazione: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
