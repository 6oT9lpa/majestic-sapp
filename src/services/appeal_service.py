from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from src.database import get_session
from src.models.appeal_model import Appeal, HelpAppeal, ComplaintAppeal, AmnestyAppeal, AppealStatus, AppealType, AppealAssignment
from src.schemas.appeal_schema import BaseAppeal, AppealResponse
from src.models.user_model import User

class AppealService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_appeal(self, appeal_data: BaseAppeal, user_id: Optional[uuid.UUID] = None):
        # Создаем основное обращение
        appeal = Appeal(
            user_id=user_id,
            type=appeal_data.type,
            status=AppealStatus.PENDING
        )
        
        self.session.add(appeal)
        await self.session.flush()
        
        # Создаем конкретный тип обращения
        if appeal_data.type == AppealType.HELP:
            help_appeal = HelpAppeal(
                appeal_id=appeal.id,
                nickname=appeal_data.nickname,
                email=appeal_data.email,
                description=appeal_data.description,
                attachment=appeal_data.attachment
            )
            self.session.add(help_appeal)
        elif appeal_data.type == AppealType.COMPLAINT:
            complaint_appeal = ComplaintAppeal(
                appeal_id=appeal.id,
                violator_nickname=appeal_data.violator_nickname,
                description=appeal_data.description,
                attachment=appeal_data.attachment
            )
            self.session.add(complaint_appeal)
        elif appeal_data.type == AppealType.AMNESTY:
            amnesty_appeal = AmnestyAppeal(
                appeal_id=appeal.id,
                admin_nickname=appeal_data.admin_nickname
            )
            self.session.add(amnesty_appeal)
        
        await self.session.commit()
        await self.session.refresh(appeal)
        
        return AppealResponse(
            id=appeal.id,
            type=appeal.type,
            status=appeal.status.value,
            created_at=appeal.created_at
        )

    async def get_appeal_by_id(self, appeal_id: uuid.UUID) -> Optional[dict]:
        """Получить обращение по ID с полной информацией"""
        result = await self.session.execute(
            select(Appeal).where(Appeal.id == appeal_id)
        )
        appeal = result.scalar()
        
        assigned = await self.session.execute(
            select(
                AppealAssignment.user_id,
                User.username
            ).join(User, User.id == AppealAssignment.user_id)
            .where(AppealAssignment.appeal_id == appeal_id)
        )

        assigned_row = assigned.first()

        assigned_user_id = None
        assigned_user_name = None

        if assigned_row:
            assigned_user_id = assigned_row[0]
            assigned_user_name = assigned_row[1]

        if not appeal:
            return None

        appeal_data = {
            "id": appeal.id,
            "type": appeal.type.value,
            "status": appeal.status.value,
            "created_at": appeal.created_at.isoformat(),
            "user_id": appeal.user_id if appeal.user_id else None,
            "assigned_moder_id": assigned_user_id,
            "assigned_moder_name": assigned_user_name,
            "description": None,
            "additional_info": {}
        }
        
        # Получаем имя пользователя
        if appeal.user_id:
            user_result = await self.session.execute(
                select(User).where(User.id == appeal.user_id))
            user = user_result.scalar()
            if user:
                appeal_data["user_name"] = user.username
        
        # Получаем описание и дополнительную информацию в зависимости от типа
        if appeal.type == AppealType.HELP:
            help_result = await self.session.execute(
                select(HelpAppeal).where(HelpAppeal.appeal_id == appeal.id))
            help_appeal = help_result.scalar()
            if help_appeal:
                appeal_data["description"] = help_appeal.description
                appeal_data["additional_info"] = {
                    "attachment": help_appeal.attachment,
                    "info_type": "help"
                }
                
        elif appeal.type == AppealType.COMPLAINT:
            complaint_result = await self.session.execute(
                select(ComplaintAppeal).where(ComplaintAppeal.appeal_id == appeal.id))
            complaint_appeal = complaint_result.scalar()
            if complaint_appeal:
                appeal_data["description"] = complaint_appeal.description
                appeal_data["additional_info"] = {
                    "attachment": complaint_appeal.attachment,
                    "violator_nickname": complaint_appeal.violator_nickname,
                    "info_type": "complaint"
                }
                
        elif appeal.type == AppealType.AMNESTY:
            amnesty_result = await self.session.execute(
                select(AmnestyAppeal).where(AmnestyAppeal.appeal_id == appeal.id))
            amnesty_appeal = amnesty_result.scalar()
            if amnesty_appeal:
                appeal_data["description"] = "Запрос амнистии"
                appeal_data["additional_info"] = {
                    "admin_nickname": amnesty_appeal.admin_nickname,
                    "info_type": "amnesty"
                }
        
        return appeal_data

    
async def get_appeal_service(session: AsyncSession = Depends(get_session)) -> AppealService:
    return AppealService(session)