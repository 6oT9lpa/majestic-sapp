from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.models.appeal_model import Appeal, AppealStatus, AppealType
from src.models.user_model import User
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_recent_activities(self, user_id: uuid.UUID, is_support: bool = False) -> List[Dict[str, Any]]:
        if is_support:
            # Для модераторов получаем последние обработанные обращения
            query = (
                select(Appeal)
                .where(Appeal.status.in_([AppealStatus.RESOLVED, AppealStatus.REJECTED, AppealStatus.IN_PROGRESS]))
                .order_by(Appeal.created_at.desc())
                .limit(5)
            )
        else:
            # Для обычных пользователей получаем их последние обращения
            query = (
                select(Appeal)
                .where(Appeal.user_id == user_id)
                .order_by(Appeal.created_at.desc())
                .limit(5)
            )
        
        result = await self.session.execute(query)
        appeals = result.unique().scalars().all()
        
        return [{
            "id": str(appeal.id),
            "type": appeal.type.value,
            "status": appeal.status.value,
            "created_at": appeal.created_at,
            "description": self._get_appeal_description(appeal)
        } for appeal in appeals]
    
    async def get_user_appeals(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        query = (
            select(Appeal)
            .where(Appeal.user_id == user_id)
            .order_by(Appeal.created_at.desc())
        )
        
        result = await self.session.execute(query)
        appeals = result.unique().scalars().all()
        
        return [{
            "id": str(appeal.id),
            "type": appeal.type.value,
            "status": appeal.status.value,
            "created_at": appeal.created_at
        } for appeal in appeals]
    
    def _get_appeal_description(self, appeal: Appeal) -> str:
        if appeal.type == AppealType.HELP:
            return "Запрос помощи"
        elif appeal.type == AppealType.COMPLAINT:
            return "Жалоба на игрока"
        elif appeal.type == AppealType.AMNESTY:
            return "Запрос амнистии"
        return "Обращение"
    
    async def get_admin_data(self, user_id: uuid.UUID) -> Dict[str, Any]:
        user_query = select(User).where(User.id == user_id)
        user_result = await self.session.execute(user_query)
        user = user_result.scalar_one()
        
        if user.role.level < 2:
            return {"access": False}
        
        users_count = await self.session.scalar(select(func.count(User.id)))
        active_appeals = await self.session.scalar(
            select(func.count(Appeal.id))
            .where(Appeal.status == AppealStatus.PENDING)
        )
        
        return {
            "access": True,
            "users_count": users_count,
            "active_appeals": active_appeals,
        }

async def get_dashboard_service(session: AsyncSession = Depends(get_session)) -> DashboardService:
    return DashboardService(session)