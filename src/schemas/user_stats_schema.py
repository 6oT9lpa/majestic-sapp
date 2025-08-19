from http import server
from pydantic import BaseModel, Field, validator
from typing import Optional

class UserStatsUpdate(BaseModel):
    username: str = Field(..., min_length=1)
    complaints_resolved: Optional[int] = Field(None, ge=0)
    complaints_rejected: Optional[int] = Field(None, ge=0)
    bans_issued: Optional[int] = Field(None, ge=0)
    delays: Optional[int] = Field(None, ge=0)
    fine: Optional[int] = Field(None, ge=0)
    server: Optional[str] = Field(None, min_length=1)

    @validator('*', pre=True)
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

class UserStatsResponse(BaseModel):
    status: str
    message: str
    updated_fields: list[str]