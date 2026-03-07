from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date, datetime


class ConfezionamentoLottoBase(BaseModel):
    lotto_id: int
    litri_utilizzati: float


class ConfezionamentoLottoOut(ConfezionamentoLottoBase):
    id: int
    lotto_codice: Optional[str] = None

    model_config = {"from_attributes": True}


class ConfezionamentoBase(BaseModel):
    codice: str = Field(..., max_length=20)
    data_confezionamento: date
    anno_campagna: int
    contenitore_id: int
    frantoio_id: Optional[int] = None
    formato: str = Field(..., max_length=30)
    capacita_litri: float
    num_unita: int
    litri_totali: float
    prezzo_imponibile: Optional[float] = None
    iva_percentuale: float = 4
    importo_iva: Optional[float] = None
    prezzo_listino: Optional[float] = None
    note: Optional[str] = None


class ConfezionamentoCreate(ConfezionamentoBase):
    lotti: List[ConfezionamentoLottoBase] = []


class ConfezionamentoUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    data_confezionamento: Optional[date] = None
    anno_campagna: Optional[int] = None
    contenitore_id: Optional[int] = None
    frantoio_id: Optional[int] = None
    formato: Optional[str] = Field(None, max_length=30)
    capacita_litri: Optional[float] = None
    num_unita: Optional[int] = None
    litri_totali: Optional[float] = None
    prezzo_imponibile: Optional[float] = None
    iva_percentuale: Optional[float] = None
    importo_iva: Optional[float] = None
    prezzo_listino: Optional[float] = None
    note: Optional[str] = None
    lotti: Optional[List[ConfezionamentoLottoBase]] = None


class ConfezionamentoOut(ConfezionamentoBase):
    id: int
    contenitore_descrizione: Optional[str] = None
    contenitore_foto: Optional[str] = None
    frantoio_denominazione: Optional[str] = None
    giacenza_unita: Optional[int] = None
    lotti: List[ConfezionamentoLottoOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
