from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CausaleMovBase(BaseModel):
    codice: str = Field(..., max_length=30)
    label: str = Field(..., max_length=80)
    tipo_movimento: str = Field(..., max_length=10)
    attivo: bool = True


class CausaleMovCreate(CausaleMovBase):
    pass


class CausaleMovUpdate(BaseModel):
    codice: Optional[str] = Field(None, max_length=30)
    label: Optional[str] = Field(None, max_length=80)
    tipo_movimento: Optional[str] = Field(None, max_length=10)
    attivo: Optional[bool] = None


class CausaleMovOut(CausaleMovBase):
    id: int
    sistema: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
