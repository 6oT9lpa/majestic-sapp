from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, validator, constr
from datetime import datetime
import uuid

class AppealType(str, Enum):
    HELP = "help"
    COMPLAINT = "complaint"
    AMNESTY = "amnesty"

class BaseAppeal(BaseModel):
    type: AppealType
    
    @validator('*', pre=True)
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

class HelpAppealCreate(BaseAppeal):
    type: AppealType = AppealType.HELP
    nickname: constr(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9 .]+$')
    email: EmailStr
    description: constr(min_length=10, max_length=1500)
    attachment: Optional[str] = None
    
    @validator('attachment')
    def validate_attachment(cls, v):
        if v and not any(domain in v for domain in ['youtube.com', 'youtu.be', 'rutube.ru', 'imgur.com', 'yapx.ru']):
            raise ValueError('Недопустимый источник доказательства. Используйте YouTube, Rutube, Imgur или Yapx')
        return v

class ComplaintAppealCreate(BaseAppeal):
    type: AppealType = AppealType.COMPLAINT
    violator_nickname: constr(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9 .]+$')
    description: constr(min_length=10, max_length=1500)
    attachment: Optional[str] = None
    
    @validator('attachment')
    def validate_attachment(cls, v):
        if v and not any(domain in v for domain in ['youtube.com', 'youtu.be', 'rutube.ru', 'imgur.com', 'yapx.ru']):
            raise ValueError('Недопустимый источник доказательства. Используйте YouTube, Rutube, Imgur или Yapx')
        return v

class AmnestyAppealCreate(BaseAppeal):
    type: AppealType = AppealType.AMNESTY
    admin_nickname: Optional[constr(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9 .]+$')] = None
    description: constr(min_length=10, max_length=1500)

class AppealResponse(BaseModel):
    id: uuid.UUID
    type: AppealType
    status: str
    created_at: datetime