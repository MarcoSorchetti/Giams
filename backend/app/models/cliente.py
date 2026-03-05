import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Validator mixin — usato solo da Create e Update (NON da Out)
# ---------------------------------------------------------------------------
class _ClienteValidators:
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

    @field_validator("cap", "consegna_cap")
    @classmethod
    def validate_cap(cls, v):
        if v and v.strip():
            if not re.match(r"^\d{5}$", v.strip()):
                raise ValueError("CAP deve essere di 5 cifre numeriche")
        return v


# ---------------------------------------------------------------------------
# Base — campi condivisi (senza validator, usato anche da Out)
# ---------------------------------------------------------------------------
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
    sconto_default: float = 0

    attivo: bool = True
    note: Optional[str] = None


class ClienteCreate(_ClienteValidators, ClienteBase):
    codice: Optional[str] = Field(None, max_length=20)  # Auto-generato se non fornito
    sconto_default: float = Field(0, ge=0, le=100)


class ClienteUpdate(_ClienteValidators, BaseModel):
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

    sconto_default: Optional[float] = Field(None, ge=0, le=100.0)
    attivo: Optional[bool] = None
    note: Optional[str] = None


class ClienteOut(ClienteBase):
    id: int
    denominazione: Optional[str] = None  # campo calcolato: nome+cognome o ragione_sociale
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
