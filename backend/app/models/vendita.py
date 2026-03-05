from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Righe vendita
# ---------------------------------------------------------------------------

class VenditaRigaBase(BaseModel):
    confezionamento_id: int
    quantita: int = Field(..., gt=0)
    prezzo_listino: Optional[float] = None
    sconto_percentuale: float = 0
    prezzo_unitario: float = Field(..., ge=0)
    importo_riga: float = Field(..., ge=0)


class VenditaRigaOut(VenditaRigaBase):
    id: int
    confezionamento_codice: Optional[str] = None
    confezionamento_formato: Optional[str] = None
    contenitore_descrizione: Optional[str] = None
    prezzo_listino: Optional[float] = None
    sconto_percentuale: float = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Vendita
# ---------------------------------------------------------------------------

class VenditaCreate(BaseModel):
    codice: str = Field(..., max_length=20)
    cliente_id: int
    data_vendita: date
    anno_campagna: int
    imponibile: float = 0
    sconto_percentuale: Optional[float] = None
    imponibile_scontato: float = 0
    iva_percentuale: float = 4
    importo_iva: float = 0
    arrotondamento: float = 0
    importo_totale: float = 0
    spedizione_indirizzo: Optional[str] = None
    spedizione_cap: Optional[str] = None
    spedizione_citta: Optional[str] = None
    spedizione_provincia: Optional[str] = None
    note: Optional[str] = None
    righe: List[VenditaRigaBase] = []


class VenditaUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    cliente_id: Optional[int] = None
    data_vendita: Optional[date] = None
    anno_campagna: Optional[int] = None
    imponibile: Optional[float] = None
    sconto_percentuale: Optional[float] = None
    imponibile_scontato: Optional[float] = None
    iva_percentuale: Optional[float] = None
    importo_iva: Optional[float] = None
    arrotondamento: Optional[float] = None
    importo_totale: Optional[float] = None
    spedizione_indirizzo: Optional[str] = None
    spedizione_cap: Optional[str] = None
    spedizione_citta: Optional[str] = None
    spedizione_provincia: Optional[str] = None
    note: Optional[str] = None
    righe: Optional[List[VenditaRigaBase]] = None


class VenditaOut(BaseModel):
    id: int
    codice: str
    cliente_id: int
    cliente_denominazione: Optional[str] = None
    data_vendita: date
    anno_campagna: int
    stato: str
    imponibile: float
    sconto_percentuale: Optional[float] = None
    imponibile_scontato: float
    iva_percentuale: float
    importo_iva: float
    arrotondamento: float = 0
    importo_totale: float
    numero_fattura: Optional[str] = None
    data_pagamento: Optional[date] = None
    modalita_pagamento: Optional[str] = None
    riferimento_pagamento: Optional[str] = None
    data_spedizione: Optional[date] = None
    numero_ddt: Optional[str] = None
    note_spedizione: Optional[str] = None
    spedizione_indirizzo: Optional[str] = None
    spedizione_cap: Optional[str] = None
    spedizione_citta: Optional[str] = None
    spedizione_provincia: Optional[str] = None
    data_conferma: Optional[date] = None
    note: Optional[str] = None
    righe: List[VenditaRigaOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Payloads per transizioni di stato
# ---------------------------------------------------------------------------

class VenditaPatchInfo(BaseModel):
    data_vendita: Optional[date] = None
    note: Optional[str] = None


class SpedisciPayload(BaseModel):
    data_spedizione: date
    numero_ddt: Optional[str] = None
    note_spedizione: Optional[str] = None
    spedizione_indirizzo: Optional[str] = None
    spedizione_cap: Optional[str] = None
    spedizione_citta: Optional[str] = None
    spedizione_provincia: Optional[str] = None


class PagaPayload(BaseModel):
    data_pagamento: date
    modalita_pagamento: Optional[str] = None
    riferimento_pagamento: Optional[str] = None
