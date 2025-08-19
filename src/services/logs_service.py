from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, Dict
import uuid

from src.database import get_session
from src.models.user_model import UserActionLog, User
from src.models.role_model import Role

class LogService:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def get_logs(
        self,
        user_id: Optional[uuid.UUID] = None,
        page: int = 1,
        per_page: int = 20,
        action_type: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> Dict:
        offset = (page - 1) * per_page
        
        query = select(
            UserActionLog.id,
            UserActionLog.action_type,
            UserActionLog.created_at,
            UserActionLog.ip_address,
            UserActionLog.action_details,
            UserActionLog.user_id,
            User.username,
            Role.name.label("role_name")
        ).join(
            User, UserActionLog.user_id == User.id, isouter=True
        ).join(
            Role, User.role_id == Role.id, isouter=True
        ).order_by(UserActionLog.created_at.desc())
        
        if action_type:
            query = query.where(UserActionLog.action_type == action_type)
            
        if user_id:
            query = query.where(UserActionLog.user_id == user_id)
        
        if search_query:
            query = query.where(
                or_(
                    UserActionLog.action_type.ilike(f"%{search_query}%"),
                    User.username.ilike(f"%{search_query}%")
                )
            )
        
        count_query = select(func.count()).select_from(query)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        result = await self.session.execute(query.offset(offset).limit(per_page))
        
        logs = []
        for row in result:
            log_data = {
                "id": row.id,
                "action_type": row.action_type,
                "created_at": row.created_at,
                "ip_address": row.ip_address,
                "action_details": row.action_details,
                "user": None
            }
            
            if row.user_id:
                log_data["user"] = {
                    "id": row.user_id,
                    "username": row.username,
                    "role": {"name": row.role_name} if row.role_name else None
                }
            
            logs.append(log_data)
        
        return {
            "logs": logs,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }

async def get_log_service(session: AsyncSession = Depends(get_session)) -> LogService:
    return LogService(session)