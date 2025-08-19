import uuid
from src.models.base_model import Base
from sqlalchemy import String, ForeignKey, UUID, Boolean, DateTime, func, TIMESTAMP, JSON, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Dict
from enum import Enum

class User(Base):
    __tablename__ = "user"
    
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    email: Mapped[str] = mapped_column(
        String(255),  
        unique=True,
        nullable=False,
        index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("role.id"),
        nullable=False
    )
    hash_pasw: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=False
    )
    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )

    override_permission = relationship("UserPermissionOverride", lazy="joined")
    role = relationship("Role", lazy="joined")
    appeals = relationship("Appeal", back_populates="user", lazy="joined")
    assignments = relationship("AppealAssignment", back_populates="user", lazy="joined")

class UserPermissionOverride(Base):
    __tablename__ = "user_permission_override"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        primary_key=True
    )
    permissions: Mapped[Dict[str, bool]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
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

class SupportAssignment(Base):
    __tablename__ = "support_assignments"
    
    support_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        primary_key=True
    )
    moderator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id")
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    
class DeletedAccount(Base):
    __tablename__ = "deleted_accounts"
    
    main_account_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    main_account_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    main_account_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    deleted_accounts_data: Mapped[Dict] = mapped_column(
        JSON,
        nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id")
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
    
class UserActionLog(Base):
    __tablename__ = "user_action_logs"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False
    )
    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    action_details: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False
    )
    user_agent: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )
    
    user = relationship("User", lazy="joined")
    
class UserHistory(Base):
    __tablename__ = "user_history"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False
    )
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str] = mapped_column(String(255), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)    

class UserRequestType(str, Enum):
    USERNAME_CHANGE = "username_change"
    ACCOUNT_DELETION = "account_deletion"

class UserRequest(Base):
    __tablename__ = "user_requests"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False
    )
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    request_data: Mapped[Dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='pending') 
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )
    resolved_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True
    )
    resolved_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=True
    )

class UserBan(Base):
    __tablename__ = "user_bans"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    banned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False
    )
    banned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    
    user = relationship("User", foreign_keys=[user_id])
    moderator = relationship("User", foreign_keys=[banned_by])

