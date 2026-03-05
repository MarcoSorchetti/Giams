import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Validator mixin — usato solo da Create e Update (NON da Out)
# ---------------------------------------------------------------------------
class _FornitoreValidators:
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v and v.strip():
            if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v.strip()):
                raise ValueError("Formato email non valido")
        return v

    @field_validator("pec")
    @classmethod
    def validate_pec(cls, v):
        if v and v.strip():
            if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v.strip()):
                raise ValueError("Formato PEC non valido")
        return v

    @field_validator("partita_iva")
    @classmethod
    def validate_partita_iva(cls, v):
        if v and v.strip():
            cleaned = v.strip().upper()
            if not re.match(r"^(\d{11}|[A-Z]{2}\d{11})$", cleaned):
                raise ValueError("Partita IVA: 11 cifre o codice paese + 11 cifre (es. IT12345678901)")
            return cleaned
        return v

    @field_validator("codice_fiscale")
    @classmethod
    def validate_codice_fiscale(cls, v):
        if v and v.strip():
            cleaned = v.strip().upper()
            if not re.match(r"^[A-Z0-9]{16}$", cleaned):
                raise ValueError("Codice Fiscale deve essere di 16 caratteri alfanumerici")
        return v

    @field_validator("cap")
    @classmethod
    def validate_cap(cls, v):
        if v and v.strip():
            if not re.match(r"^\d{5}$", v.strip()):
                raise ValueError("CAP deve essere di 5 cifre numeriche")
        return v

    @field_validator("iban")
    @classmethod
    def validate_iban(cls, v):
        if v and v.strip():
            cleaned = v.strip().upper().replace(" ", "")
            if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$", cleaned):
                raise ValueError("Formato IBAN non valido (es. IT60X0542811101000000123456)")
        return v


# ---------------------------------------------------------------------------
# Base — campi condivisi (senza validator, usato anche da Out)
# ---------------------------------------------------------------------------
class FornitoreBase(BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    tipo_fornitore: str = Field(..., max_length=10)

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


class FornitoreCreate(_FornitoreValidators, FornitoreBase):
    pass


class FornitoreUpdate(_FornitoreValidators, BaseModel):
    codice: Optional[str] = Field(None, max_length=20)
    tipo_fornitore: Optional[str] = Field(None, max_length=10)

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
