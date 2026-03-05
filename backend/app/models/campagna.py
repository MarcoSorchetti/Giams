from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class CampagnaBase(BaseModel):
    anno: int
    data_inizio: Optional[date] = None
    data_fine: Optional[date] = None
    note: Optional[str] = None


class CampagnaCreate(CampagnaBase):
    pass


class CampagnaUpdate(BaseModel):
    anno: Optional[int] = None
    data_inizio: Optional[date] = None
    data_fine: Optional[date] = None
    note: Optional[str] = None


class CampagnaOut(CampagnaBase):
    id: int
    stato: str = "aperta"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
