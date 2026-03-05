from typing import Optional
from pydantic import BaseModel, Field
from datetime import date, datetime


class CostoBase(BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    categoria_id: int
    anno_campagna: int
    descrizione: str = Field(..., max_length=200)
    fornitore_id: Optional[int] = None
    data_fattura: date
    numero_fattura: Optional[str] = Field(None, max_length=50)
    tipo_documento: str = Field("fattura", max_length=20)
    imponibile: float
    iva_percentuale: float = 22.0
    importo_iva: Optional[float] = None
    importo_totale: Optional[float] = None
    data_pagamento: Optional[date] = None
    modalita_pagamento: Optional[str] = Field(None, max_length=20)
    riferimento_pagamento: Optional[str] = Field(None, max_length=50)
    stato_pagamento: str = Field("da_pagare", max_length=15)
    anni_ammortamento: int = 0
    note: Optional[str] = None


class CostoCreate(CostoBase):
    imponibile: float = Field(..., ge=0)
    iva_percentuale: float = Field(22.0, ge=0, le=100)


class CostoUpdate(BaseModel):
    categoria_id: Optional[int] = None
    anno_campagna: Optional[int] = None
    descrizione: Optional[str] = Field(None, max_length=200)
    fornitore_id: Optional[int] = None
    data_fattura: Optional[date] = None
    numero_fattura: Optional[str] = Field(None, max_length=50)
    tipo_documento: Optional[str] = Field(None, max_length=20)
    imponibile: Optional[float] = Field(None, ge=0)
    iva_percentuale: Optional[float] = Field(None, ge=0, le=100)
    importo_iva: Optional[float] = None
    importo_totale: Optional[float] = None
    data_pagamento: Optional[date] = None
    modalita_pagamento: Optional[str] = Field(None, max_length=20)
    riferimento_pagamento: Optional[str] = Field(None, max_length=50)
    stato_pagamento: Optional[str] = Field(None, max_length=15)
    anni_ammortamento: Optional[int] = None
    note: Optional[str] = None


class CostoOut(CostoBase):
    id: int
    categoria_nome: Optional[str] = None
    categoria_tipo: Optional[str] = None
    fornitore_denominazione: Optional[str] = None
    quota_ammortamento: Optional[float] = None
    documento: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
