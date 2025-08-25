from src.models.appeal_model import AppealMessage, Appeal, AppealAssignment, AppealAssignmentHistory
from src.models.user_model import SupportAssignment, User
from src.database import get_session
from src.models.appeal_model import AppealMessage

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from fastapi import Depends, UploadFile, HTTPException
from pathlib import Path
from datetime import datetime
import uuid

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_PATH = PROJECT_ROOT / "storage/files"
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}

class MessangerService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_appeal_message(
        self,
        appeal_id: uuid.UUID,
        user_id: uuid.UUID,
        message: str,
        is_system: bool = False,
        attachment_ids: List[str] = None
    ) -> dict:
        """Сохранить сообщение обращения"""
        message_metadata = {}
        if attachment_ids:
            message_metadata["attachments"] = attachment_ids  

        appeal_message = AppealMessage(
            appeal_id=appeal_id,
            user_id=user_id,
            message=message,
            is_system=is_system,
            message_metadata=message_metadata 
        )

        self.session.add(appeal_message)
        await self.session.commit()
        await self.session.refresh(appeal_message)

        return {
            "id": str(appeal_message.id),
            "appeal_id": str(appeal_message.appeal_id),
            "user_id": str(appeal_message.user_id),
            "message": appeal_message.message,
            "is_system": appeal_message.is_system,
            "created_at": appeal_message.created_at.isoformat(),
            "message_metadata": message_metadata  
        }
    
    async def save_attachments(
        self,
        files: List[UploadFile],
        appeal_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[dict]:
        """Сохранить прикрепленные файлы"""
        if not files:
            return []
        
        appeal_path = STORAGE_PATH / str(appeal_id)
        appeal_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        for file in files:
            file_size = 0
            for chunk in file.file:
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Файл {file.filename} слишком большой. Максимальный размер 10MB"
                    )
            
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Недопустимый формат файла {file.filename}. Разрешены только PNG, JPEG, GIF"
                )
            
            file_id = uuid.uuid4()
            file_name = f"{file_id}{file_ext}"
            file_path = appeal_path / file_name
            
            with open(file_path, "wb") as buffer:
                file.file.seek(0)
                buffer.write(file.file.read())
            
            saved_files.append({
                "original_name": file.filename,
                "saved_name": file_name,
                "size": file_size,
                "extension": file_ext,
                "path": str(file_path.relative_to(STORAGE_PATH))
            })
        
        return saved_files
    
    async def get_attachments_info(
        self,
        appeal_id: uuid.UUID
    ) -> List[dict]:
        """Получить информацию о прикрепленных файлах"""
        appeal_path = STORAGE_PATH / str(appeal_id)
        
        if not appeal_path.exists():
            return []
        
        attachments = []
        
        for file_path in appeal_path.iterdir():
            if file_path.is_file():
                file_ext = file_path.suffix.lower()
                if file_ext in ALLOWED_EXTENSIONS:
                    attachments.append({
                        "name": file_path.name,
                        "original_name": file_path.name,  
                        "size": file_path.stat().st_size,
                        "extension": file_ext,
                        "path": str(file_path.relative_to(STORAGE_PATH))
                    })
        
        return attachments
    
    async def update_appeal_status(
        self,
        appeal_id: uuid.UUID,
        new_status: str,
        assigned_to: uuid.UUID = None,
        assigned_by: uuid.UUID = None
    ):
        """Обновить статус обращения и назначить модератора"""
        result = await self.session.execute(
            select(Appeal).where(Appeal.id == appeal_id)
        )
        appeal = result.scalar()
        
        if not appeal:
            raise ValueError("Appeal not found")
        
        appeal.status = new_status
        
        if assigned_to:
            await self.session.execute(
                update(AppealAssignment)
                .where(
                    and_(
                        AppealAssignment.appeal_id == appeal_id,
                        AppealAssignment.released_at == None
                    )
                )
                .values(released_at=func.now())
            )
            
            assignment = AppealAssignment(
                appeal_id=appeal_id,
                user_id=assigned_to,
                assigned_at=func.now()
            )
            self.session.add(assignment)
            
            if assigned_by:
                await self.notify_moderator_assignment(appeal_id, assigned_to, assigned_by)
        
        await self.session.commit()
        await self.notify_appeal_update(appeal_id, "status_changed")
    
    async def reassign_appeal(
        self,
        appeal_id: uuid.UUID,
        reassign_type: str,
        current_user_id: uuid.UUID
    ):
        """Переназначить обращение с учетом что у модератора может быть несколько саппортов"""
        # Получаем обращение
        appeal = await self.session.get(Appeal, appeal_id)
        if not appeal:
            raise ValueError("Appeal not found")

        # Получаем текущее назначение
        current_assignment = await self.session.execute(
            select(AppealAssignment)
            .where(
                and_(
                    AppealAssignment.appeal_id == appeal_id,
                    AppealAssignment.released_at == None
                )
            )
        )
        current_assignment = current_assignment.unique().scalar_one_or_none()

        # Закрываем текущее назначение
        if current_assignment:
            current_assignment.released_at = func.now()
            current_assignment.is_auto_released = False

        new_moderator_id = None
        system_message = ""

        if reassign_type == 'unassign':
            # Тип 1: Снять модератора
            appeal.status = "pending"
            system_message = "Модератор снят с обращения. Ожидает нового назначения."
            
            if current_assignment:
                history = AppealAssignmentHistory(
                    appeal_id=appeal_id,
                    user_id=current_assignment.user_id,
                    assigned_at=current_assignment.assigned_at,
                    released_at=func.now(),
                    is_auto_released=False,
                    cannot_reassign=True
                )
                self.session.add(history)

        elif reassign_type == 'to_support_moderator':
            # Тип 2: Переназначить на закрепленного модератора
            support_assignment = await self.session.execute(
                select(SupportAssignment)
                .where(
                    and_(
                        SupportAssignment.support_id == current_user_id,
                        SupportAssignment.is_active == True
                    )
                )
                .order_by(SupportAssignment.assigned_at.desc())
                .limit(1)
            )
            support_assignment = support_assignment.unique().scalar_one_or_none()
            
            if not support_assignment:
                raise ValueError("No active moderator assigned to this support")

            new_moderator_id = support_assignment.moderator_id
            appeal.status = "in_progress"
            
            # Создаем новое назначение
            new_assignment = AppealAssignment(
                appeal_id=appeal_id,
                user_id=new_moderator_id,
                assigned_at=func.now()
            )
            self.session.add(new_assignment)
            
            # Получаем имя модератора
            moderator = await self.session.get(User, new_moderator_id)
            moderator_name = moderator.username if moderator else "модератора"
            
            system_message = f"Обращение переназначено на {moderator_name} (закрепленный модератор)"

        # Сохраняем системное сообщение
        if system_message:
            system_msg = AppealMessage(
                appeal_id=appeal_id,
                user_id=current_user_id,
                message=system_message,
                is_system=True
            )
            self.session.add(system_msg)
        
        await self.session.commit()
        
        await self.notify_appeal_update(appeal_id, "reassigned")

    async def close_appeal(
        self,
        appeal_id: uuid.UUID,
        status: str = "resolved"
    ):
        """Закрыть обращение"""
        result = await self.session.execute(
            select(Appeal).where(Appeal.id == appeal_id)
        )
        appeal = result.scalar()
        
        if not appeal:
            raise ValueError("Appeal not found")
        
        # Освобождаем текущего модератора
        await self.session.execute(
            update(AppealAssignment)
            .where(
                and_(
                    AppealAssignment.appeal_id == appeal_id,
                    AppealAssignment.released_at == None
                )
            )
            .values(released_at=func.now())
        )
        
        appeal.status = status
        await self.notify_appeal_update(appeal_id, "closed")
        await self.session.commit()

    async def get_appeal_messages(
        self,
        appeal_id: uuid.UUID
    ) -> List[dict]:
        """Получить сообщения обращения"""
        result = await self.session.execute(
            select(AppealMessage)
            .where(AppealMessage.appeal_id == appeal_id)
            .order_by(AppealMessage.created_at))
        
        messages = []
        for msg in result.scalars():
            message_data = {
                "id": str(msg.id),
                "appeal_id": str(msg.appeal_id),
                "user_id": str(msg.user_id),
                "message": msg.message,
                "is_system": msg.is_system,
                "created_at": msg.created_at.isoformat()
            }
            
            # Добавляем metadata, если она есть
            if msg.message_metadata:
                message_data["message_metadata"] = msg.message_metadata
                
            messages.append(message_data)
        
        return messages
    
    async def notify_appeal_update(self, appeal_id: uuid.UUID, action: str = "update"):
        """Уведомить всех о изменении обращения"""
        from src.websoket import manager
        
        appeal_data = await self.get_appeal_data_for_broadcast(appeal_id)
        if not appeal_data:
            return
        
        message = {
            "type": f"appeal_{action}",
            "appeal": appeal_data,
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast_appeal_update(message)
        
        counters_message = {
            "type": "counters_update",
            "counters": await self.get_appeals_counters()
        }
        await manager.broadcast_appeal_update(counters_message)

    async def get_appeals_counters(self) -> dict:
        """Получить актуальные счетчики обращений"""
        from sqlalchemy import select, func, and_
        
        # Счетчик необработанных обращений
        pending_result = await self.session.execute(
            select(func.count()).select_from(Appeal).where(
                Appeal.status == "pending"
            )
        )
        pending = pending_result.scalar() or 0
        
        return {
            "pending": pending,
            "user_assigned": 0  
        }

    async def get_appeal_data_for_broadcast(self, appeal_id: uuid.UUID) -> dict:
        """Получить данные обращения для broadcast"""
        result = await self.session.execute(
            select(Appeal).where(Appeal.id == appeal_id)
        )
        appeal = result.scalar()
        
        if not appeal:
            return None
        
        return {
            "id": str(appeal.id),
            "type": appeal.type,
            "status": appeal.status,
            "user_id": str(appeal.user_id) if appeal.user_id else None,
            "assigned_to": await self.get_assigned_moderator(appeal.id),
            "updated_at": datetime.now().isoformat()
        }

    async def get_assigned_moderator(self, appeal_id: uuid.UUID) -> Optional[str]:
        """Получить ID назначенного модератора"""
        result = await self.session.execute(
            select(AppealAssignment.user_id)
            .where(
                and_(
                    AppealAssignment.appeal_id == appeal_id,
                    AppealAssignment.released_at == None
                )
            )
        )
        assignment = result.scalar_one_or_none()
        return str(assignment) if assignment else None
    
    async def notify_moderator_assignment(
        self,
        appeal_id: uuid.UUID,
        moderator_id: uuid.UUID,
        assigned_by: uuid.UUID
    ):
        """Отправить уведомление модератору о новом назначении"""
        from src.websoket import manager
        
        # Получаем информацию о том, кто назначил
        assigned_by_user = await self.session.get(User, assigned_by)
        assigned_by_name = assigned_by_user.username if assigned_by_user else "Система"
        
        await manager.notify_moderator_assignment(
            str(appeal_id),
            str(moderator_id),
            assigned_by_name
        )
    
async def get_messager_service(session: AsyncSession = Depends(get_session)) -> MessangerService:
    return MessangerService(session)