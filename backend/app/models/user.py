from typing import Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserOut(UserBase):
    id: int

    model_config = {"from_attributes": True}
