from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    is_active: bool = True
    is_admin: bool = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserOut(UserBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
