from src.models.base_model import Base
from sqlalchemy import String, Integer, Boolean, JSON, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum
from typing import Dict
from datetime import datetime

class PermissionLevel(int, Enum):
    USER = 1                       # Обычный пользователь
    JUNIOR_MODERATOR = 2           # Начинающий модератор
    MODERATOR = 3                  # Модератор
    MULTI_ACCOUNT_MODERATOR = 4    # Модератор по мультиаккаунтам
    MODERATOR_SUPERVISOR = 5       # Супервайзер модераторов
    CHIEF_CURATOR = 6              # Чиф куратор
    LEAD_ADMINISTRATOR = 7         # Главный администратор
    FORUM_MODERATOR = 8            # Модератор форума
    EXECUTIVE_MODERATOR = 9        # Руководство

class PermissionType(str, Enum):
    SUPPORT_REPLY = (
        "respond_support_tickets",
        PermissionLevel.JUNIOR_MODERATOR
    ) # Ответ на обращение о помощи
    ELIGIBLE_AS_MENTOR = (
        "eligible_as_mentor", 
        PermissionLevel.MODERATOR
    ) # Наставник
    MANAGE_MULTI_ACCOUNTS = (
        "manage_multi_accounts", 
        PermissionLevel.MULTI_ACCOUNT_MODERATOR
    ) # Учет мулти аккаунтов
    VIEW_ACTIVE_CHATS = (
        "view_active_chats", 
        PermissionLevel.MODERATOR_SUPERVISOR
    ) # Пользователь видит все обращения
    MANAGE_REPORTS = (
        "manage_reports", 
        PermissionLevel.MODERATOR_SUPERVISOR
    ) # Возможности вести отчетсность
    RESPOND_MODERATION_COMPLAINTS = (
        "respond_moderation_complaints", 
        PermissionLevel.CHIEF_CURATOR
    ) # Ответ на жалобы   
    RESPOND_AMNESTY_REQUESTS = (
        "respond_amnesty_requests", 
        PermissionLevel.LEAD_ADMINISTRATOR
    ) # Ответ на амнистии

    MANAGE_ROLES = ("manage_roles", PermissionLevel.FORUM_MODERATOR)
    MANAGE_USERS = ("manage_users", PermissionLevel.FORUM_MODERATOR)
    DELETE_USERS = ("delete_users", PermissionLevel.FORUM_MODERATOR)
    
    def __new__(cls, value, level):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.level = level
        return obj
    
class Role(Base):
    __tablename__ = "role"
    
    name: Mapped[str] = mapped_column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True
    )
    description: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )
    level: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=PermissionLevel.USER
    )
    default_role: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False
    )
    permissions: Mapped[Dict[str, bool]] = mapped_column(
        JSON,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )



