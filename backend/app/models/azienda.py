from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AziendaBase(BaseModel):
    ragione_sociale: str = Field(..., max_length=200)
    forma_giuridica: Optional[str] = Field(None, max_length=30)
    partita_iva: Optional[str] = Field(None, max_length=16)
    codice_fiscale: Optional[str] = Field(None, max_length=16)
    rea: Optional[str] = Field(None, max_length=30)
    codice_ateco: Optional[str] = Field(None, max_length=10)
    pec: Optional[str] = Field(None, max_length=100)
    codice_sdi: Optional[str] = Field(None, max_length=7)
    # Sede legale
    sede_legale_indirizzo: Optional[str] = Field(None, max_length=200)
    sede_legale_cap: Optional[str] = Field(None, max_length=5)
    sede_legale_citta: Optional[str] = Field(None, max_length=100)
    sede_legale_provincia: Optional[str] = Field(None, max_length=2)
    # Sede operativa
    sede_operativa_indirizzo: Optional[str] = Field(None, max_length=200)
    sede_operativa_cap: Optional[str] = Field(None, max_length=5)
    sede_operativa_citta: Optional[str] = Field(None, max_length=100)
    sede_operativa_provincia: Optional[str] = Field(None, max_length=2)
    # Contatti
    telefono: Optional[str] = Field(None, max_length=20)
    cellulare: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    sito_web: Optional[str] = Field(None, max_length=200)
    # Altro
    banca_id: Optional[int] = None
    logo_path: Optional[str] = Field(None, max_length=200)
    rappresentante_legale: Optional[str] = Field(None, max_length=200)
    capitale_sociale: Optional[float] = None
    note: Optional[str] = None


class AziendaUpdate(AziendaBase):
    ragione_sociale: Optional[str] = Field(None, max_length=200)


class AziendaOut(AziendaBase):
    id: int
    banca_denominazione: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
