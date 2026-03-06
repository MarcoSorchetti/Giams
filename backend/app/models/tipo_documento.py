from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TipoDocumentoBase(BaseModel):
    valore: str = Field(..., max_length=30)
    etichetta: str = Field(..., max_length=80)
    attivo: bool = True
    ordine: int = 0


class TipoDocumentoCreate(TipoDocumentoBase):
    pass


class TipoDocumentoUpdate(BaseModel):
    valore: Optional[str] = Field(None, max_length=30)
    etichetta: Optional[str] = Field(None, max_length=80)
    attivo: Optional[bool] = None
    ordine: Optional[int] = None


class TipoDocumentoOut(TipoDocumentoBase):
    id: int
    sistema: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
