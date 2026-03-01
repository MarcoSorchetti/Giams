from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContenitoreBase(BaseModel):
    codice: str = Field(..., max_length=30)
    descrizione: str = Field(..., max_length=100)
    capacita_litri: float
    attivo: bool = True


class ContenitoreCreate(ContenitoreBase):
    pass


class ContenitoreUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=30)
    descrizione: Optional[str] = Field(None, max_length=100)
    capacita_litri: Optional[float] = None
    attivo: Optional[bool] = None


class ContenitoreOut(ContenitoreBase):
    id: int
    foto: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
