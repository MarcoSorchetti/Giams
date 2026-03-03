from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClienteBase(BaseModel):
    codice: str = Field(..., max_length=20)
    tipo_cliente: str = Field(..., max_length=10)

    # Anagrafica privato
    nome: Optional[str] = Field(None, max_length=50)
    cognome: Optional[str] = Field(None, max_length=50)
    codice_fiscale: Optional[str] = Field(None, max_length=16)

    # Anagrafica azienda
    ragione_sociale: Optional[str] = Field(None, max_length=150)
    partita_iva: Optional[str] = Field(None, max_length=13)
    codice_sdi: Optional[str] = Field(None, max_length=7)
    pec: Optional[str] = Field(None, max_length=100)
    referente_nome: Optional[str] = Field(None, max_length=100)
    referente_telefono: Optional[str] = Field(None, max_length=20)

    # Indirizzo fatturazione
    indirizzo: Optional[str] = Field(None, max_length=150)
    cap: Optional[str] = Field(None, max_length=5)
    citta: Optional[str] = Field(None, max_length=100)
    provincia: Optional[str] = Field(None, max_length=2)

    # Indirizzo consegna
    consegna_indirizzo: Optional[str] = Field(None, max_length=150)
    consegna_cap: Optional[str] = Field(None, max_length=5)
    consegna_citta: Optional[str] = Field(None, max_length=100)
    consegna_provincia: Optional[str] = Field(None, max_length=2)

    # Contatti
    email: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)

    # Commerciale
    sconto_default: Optional[float] = None

    attivo: bool = True
    note: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    tipo_cliente: Optional[str] = Field(None, max_length=10)

    nome: Optional[str] = Field(None, max_length=50)
    cognome: Optional[str] = Field(None, max_length=50)
    codice_fiscale: Optional[str] = Field(None, max_length=16)

    ragione_sociale: Optional[str] = Field(None, max_length=150)
    partita_iva: Optional[str] = Field(None, max_length=13)
    codice_sdi: Optional[str] = Field(None, max_length=7)
    pec: Optional[str] = Field(None, max_length=100)
    referente_nome: Optional[str] = Field(None, max_length=100)
    referente_telefono: Optional[str] = Field(None, max_length=20)

    indirizzo: Optional[str] = Field(None, max_length=150)
    cap: Optional[str] = Field(None, max_length=5)
    citta: Optional[str] = Field(None, max_length=100)
    provincia: Optional[str] = Field(None, max_length=2)

    consegna_indirizzo: Optional[str] = Field(None, max_length=150)
    consegna_cap: Optional[str] = Field(None, max_length=5)
    consegna_citta: Optional[str] = Field(None, max_length=100)
    consegna_provincia: Optional[str] = Field(None, max_length=2)

    email: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)

    sconto_default: Optional[float] = None
    attivo: Optional[bool] = None
    note: Optional[str] = None


class ClienteOut(ClienteBase):
    id: int
    denominazione: Optional[str] = None  # campo calcolato: nome+cognome o ragione_sociale
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
