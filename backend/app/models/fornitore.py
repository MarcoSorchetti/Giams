from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FornitoreBase(BaseModel):
    codice: str = Field(..., max_length=20)
    tipo_fornitore: str = Field(..., max_length=10)

    # Anagrafica privato
    nome: Optional[str] = Field(None, max_length=50)
    cognome: Optional[str] = Field(None, max_length=50)
    codice_fiscale: Optional[str] = Field(None, max_length=16)

    # Anagrafica azienda
    ragione_sociale: Optional[str] = Field(None, max_length=150)
    partita_iva: Optional[str] = Field(None, max_length=11)
    codice_sdi: Optional[str] = Field(None, max_length=7)
    pec: Optional[str] = Field(None, max_length=100)
    referente_nome: Optional[str] = Field(None, max_length=100)
    referente_telefono: Optional[str] = Field(None, max_length=20)

    # Indirizzo sede
    indirizzo: Optional[str] = Field(None, max_length=150)
    cap: Optional[str] = Field(None, max_length=5)
    citta: Optional[str] = Field(None, max_length=100)
    provincia: Optional[str] = Field(None, max_length=2)

    # Contatti
    email: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)

    # Dati bancari
    iban: Optional[str] = Field(None, max_length=34)
    banca: Optional[str] = Field(None, max_length=100)

    # Classificazione
    categoria_merceologica: Optional[str] = Field(None, max_length=50)
    condizioni_pagamento: Optional[str] = Field(None, max_length=100)

    attivo: bool = True
    note: Optional[str] = None


class FornitoreCreate(FornitoreBase):
    pass


class FornitoreUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    tipo_fornitore: Optional[str] = Field(None, max_length=10)

    nome: Optional[str] = Field(None, max_length=50)
    cognome: Optional[str] = Field(None, max_length=50)
    codice_fiscale: Optional[str] = Field(None, max_length=16)

    ragione_sociale: Optional[str] = Field(None, max_length=150)
    partita_iva: Optional[str] = Field(None, max_length=11)
    codice_sdi: Optional[str] = Field(None, max_length=7)
    pec: Optional[str] = Field(None, max_length=100)
    referente_nome: Optional[str] = Field(None, max_length=100)
    referente_telefono: Optional[str] = Field(None, max_length=20)

    indirizzo: Optional[str] = Field(None, max_length=150)
    cap: Optional[str] = Field(None, max_length=5)
    citta: Optional[str] = Field(None, max_length=100)
    provincia: Optional[str] = Field(None, max_length=2)

    email: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)

    iban: Optional[str] = Field(None, max_length=34)
    banca: Optional[str] = Field(None, max_length=100)

    categoria_merceologica: Optional[str] = Field(None, max_length=50)
    condizioni_pagamento: Optional[str] = Field(None, max_length=100)

    attivo: Optional[bool] = None
    note: Optional[str] = None


class FornitoreOut(FornitoreBase):
    id: int
    denominazione: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
