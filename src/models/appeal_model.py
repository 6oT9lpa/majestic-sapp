from src.models.base_model import Base
from sqlalchemy import String, Text, ForeignKey, UUID, DateTime, Enum, Boolean, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from enum import Enum as PyEnum
import uuid
from datetime import datetime

class AppealStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"

class AppealType(str, PyEnum):
    HELP = "help"
    COMPLAINT = "complaint"
    AMNESTY = "amnesty"

class Appeal(Base):
    __tablename__ = "appeals"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=True
    )
    type: Mapped[AppealType] = mapped_column(
        Enum(AppealType),
        nullable=False
    )
    status: Mapped[AppealStatus] = mapped_column(
        Enum(AppealStatus),
        default=AppealStatus.PENDING,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    user = relationship("User", back_populates="appeals", lazy="joined")
    assignments = relationship("AppealAssignment", back_populates="appeal", lazy="joined")
    attachments = relationship("AppealAttachment", back_populates="appeal", lazy="joined")

class HelpAppeal(Base):
    __tablename__ = "help_appeals"
    
    appeal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appeals.id"),
        primary_key=True
    )
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    attachment: Mapped[str] = mapped_column(String(255), nullable=True)

class ComplaintAppeal(Base):
    __tablename__ = "complaint_appeals"
    
    appeal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appeals.id"),
        primary_key=True
    )
    violator_nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    attachment: Mapped[str] = mapped_column(String(255), nullable=True)

class AmnestyAppeal(Base):
    __tablename__ = "amnesty_appeals"
    
    appeal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appeals.id"),
        primary_key=True
    )
    admin_nickname: Mapped[str] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
class AppealMessage(Base):
    __tablename__ = "appeal_messages"
    
    appeal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appeals.id"),
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False
    )
    message: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    message_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

class AppealAttachment(Base):
    __tablename__ = "appeal_attachments"
    
    appeal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appeals.id"),
        nullable=False
    )
    file_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    appeal = relationship("Appeal", back_populates="attachments")
    user = relationship("User")

class AppealAssignment(Base):
    __tablename__ = "appeal_assignments"
    
    appeal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appeals.id"),
        primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    released_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    is_auto_released: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    
    user = relationship("User", back_populates="assignments", lazy="joined")
    appeal = relationship("Appeal", back_populates="assignments", lazy="joined")
    
class AppealAssignmentHistory(Base):
    __tablename__ = "appeal_assignment_history"
    
    appeal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appeals.id"),
        primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
    released_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
    is_auto_released: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    cannot_reassign: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )