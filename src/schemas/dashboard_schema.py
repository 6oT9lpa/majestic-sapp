from datetime import datetime
from typing import  Optional
from pydantic import BaseModel, validator, HttpUrl
from enum import Enum
import re

class ActivityType(str, Enum):
    HELP = "help"
    COMPLAINT = "complaint"
    AMNESTY = "amnesty"

class ActivityStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"

class RecentActivity(BaseModel):
    id: str
    type: ActivityType
    status: ActivityStatus
    created_at: datetime
    description: Optional[str] = None

class UserAppeal(BaseModel):
    id: str
    type: ActivityType
    status: ActivityStatus
    created_at: datetime

class StatsResponse(BaseModel):
    closed_complaints: int
    rejected: int
    bans: int
    missed_deadlines: int
    bonus: int
    pending: int
    penalty: int
    total_without_penalty: int
    total_payment: int
    payment_status: str

class ForumUrlSchema(BaseModel):
    url: str
    
    @validator('url')
    def validate_forum_url(cls, v):
        # Проверяем базовую структуру URL
        if not v.startswith('https://forum.majestic-rp.ru/members/'):
            raise ValueError('URL должен начинаться с https://forum.majestic-rp.ru/members/')
        
        # Проверяем наличие username и id в конце
        parts = v.strip('/').split('/')
        if len(parts) < 5:
            raise ValueError('Некорректный формат URL')
            
        username_part = parts[-1]
        if '.' not in username_part:
            raise ValueError('URL должен содержать имя пользователя и ID в формате username.id')
            
        username, user_id = username_part.split('.')
        if not user_id.isdigit():
            raise ValueError('ID пользователя должен быть числом')
            
        return v
    
    @property
    def username(self) -> str:
        parts = self.url.strip('/').split('/')
        username_part = parts[-1]
        return username_part.split('.')[0]
    
    @property
    def user_id(self) -> int:
        parts = self.url.strip('/').split('/')
        username_part = parts[-1]
        return int(username_part.split('.')[1])