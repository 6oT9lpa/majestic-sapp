from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import  and_, func, or_, cast, String
from typing import List, Optional, Dict
import uuid

from src.database import get_session
from src.models.user_model import SupportAssignment, User, DeletedAccount, UserHistory, UserRequest, UserBan, UserRequestType
from src.models.appeal_model import (
    Appeal,
    AppealStatus,
    AppealType,
    HelpAppeal,
    ComplaintAppeal,
    AmnestyAppeal,
    AppealAssignment
)
from src.models.role_model import Role, PermissionLevel


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def get_appeals(
        self,
        current_user: Dict,
        status: List[AppealStatus],
        type: Optional[AppealType] = None,
        assigned_to_me: Optional[bool] = False,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        allowed_types: Optional[List[str]] = None 
    ) -> dict:
        """Получить список обращений с фильтрацией"""
        offset = (page - 1) * per_page
        
        # Основной запрос для получения данных
        query = select(Appeal).where(Appeal.status.in_(status))
        
        if allowed_types:
            allowed_type_enums = [AppealType(t) for t in allowed_types]
            query = query.where(Appeal.type.in_(allowed_type_enums))
        elif type:
            query = query.where(Appeal.type == type)
        
        if assigned_to_me:
            query = query.join(
                AppealAssignment,
                AppealAssignment.appeal_id == Appeal.id
            ).where(
                and_(
                    AppealAssignment.user_id == current_user["id"],
                    AppealAssignment.released_at == None
                )
            )
        
        if search:
            search = f"%{search}%"
            help_subq = select(HelpAppeal.appeal_id).where(HelpAppeal.description.ilike(search))
            complaint_subq = select(ComplaintAppeal.appeal_id).where(ComplaintAppeal.description.ilike(search))
            
            user_subq = select(User.id).where(User.username.ilike(search))
            moderator_subq = select(AppealAssignment.appeal_id).join(
                User, AppealAssignment.user_id == User.id
            ).where(User.username.ilike(search))
            
            query = query.where(
                or_(
                    cast(Appeal.id, String).ilike(search),  
                    Appeal.user_id.in_(user_subq),      
                    Appeal.id.in_(help_subq),              
                    Appeal.id.in_(complaint_subq),        
                    Appeal.id.in_(moderator_subq)         
                )
            )
        
        # Запрос для подсчета общего количества
        count_query = select(func.count()).select_from(query)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Получаем данные для текущей страницы
        result = await self.session.execute(
            query.order_by(Appeal.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        appeals = result.unique().scalars().all()
        
        # Остальной код метода остается без изменений
        appeals_data = []
        for appeal in appeals:
            appeal_data = {
                "id": str(appeal.id),
                "type": appeal.type.value,
                "status": appeal.status.value,
                "created_at": appeal.created_at.isoformat(),
                "user_id": str(appeal.user_id) if appeal.user_id else None,
                "user_name": None,
                "description": None,
                "assigned_to": None
            }
            
            # Получаем имя пользователя
            if appeal.user_id:
                user_result = await self.session.execute(
                    select(User).where(User.id == appeal.user_id)
                )
                user = user_result.scalar()
                if user:
                    appeal_data["user_name"] = user.username
            
            # Получаем специфичные данные для типа обращения
            if appeal.type == AppealType.HELP:
                help_result = await self.session.execute(
                    select(HelpAppeal).where(HelpAppeal.appeal_id == appeal.id))
                help_appeal = help_result.scalar()
                if help_appeal:
                    appeal_data["description"] = help_appeal.description
                    
            elif appeal.type == AppealType.COMPLAINT:
                complaint_result = await self.session.execute(
                    select(ComplaintAppeal).where(ComplaintAppeal.appeal_id == appeal.id))
                complaint_appeal = complaint_result.scalar()
                if complaint_appeal:
                    appeal_data["description"] = complaint_appeal.description
                    
            elif appeal.type == AppealType.AMNESTY:
                amnesty_result = await self.session.execute(
                    select(AmnestyAppeal).where(AmnestyAppeal.appeal_id == appeal.id))
                amnesty_appeal = amnesty_result.scalar()
                if amnesty_appeal:
                    appeal_data["description"] = "Запрос амнистии"
            
            # Получаем информацию о назначении
            assignment_result = await self.session.execute(
                select(AppealAssignment)
                .where(
                    and_(
                        AppealAssignment.appeal_id == appeal.id,
                        AppealAssignment.released_at == None
                    )
                )
            )
            assignment = assignment_result.unique().scalar()
            if assignment:
                # Получаем имя назначенного модератора
                moderator_result = await self.session.execute(
                    select(User).where(User.id == assignment.user_id)
                )
                moderator = moderator_result.unique().scalar()
                if moderator:
                    appeal_data["assigned_to"] = moderator.username
                
            appeals_data.append(appeal_data)
        
        return {
            "appeals": appeals_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
        
    async def get_support_moderator(self, support_id: uuid.UUID) -> Optional[dict]:
        """Получить активного закрепленного модератора для саппорта"""
        # Получаем активне назначение текущего саппорта
        result = await self.session.execute(
            select(SupportAssignment, User)
            .join(User, SupportAssignment.moderator_id == User.id)
            .where(
                and_(
                    SupportAssignment.support_id == support_id,
                    SupportAssignment.is_active == True
                )
            )
            .order_by(SupportAssignment.assigned_at.desc())
            .limit(1)
        )
        
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            return None
        
        support_assignment, moderator = assignment
        
        # Получаем всех саппортов этого модератора
        support_result = await self.session.execute(
            select(SupportAssignment, User)
            .join(User, SupportAssignment.support_id == User.id)
            .where(
                and_(
                    SupportAssignment.moderator_id == moderator.id,
                    SupportAssignment.is_active == True
                )
            )
        )
        
        support_assignments = support_result.all()
        
        return {
            "moderator": {
                "id": str(moderator.id),
                "name": moderator.username,
                "email": moderator.email
            },
            "support_team": [
                {
                    "id": str(support.id),
                    "name": support.username,
                    "email": support.email
                } for _, support in support_assignments
            ]
        }

    async def get_deleted_accounts(
        self,
        page: int = 1,
        per_page: int = 20
    ) -> dict:
        """Получить список удаленных аккаунтов"""
        offset = (page - 1) * per_page
        
        query = select(DeletedAccount)
        
        count_query = select(func.count()).select_from(query)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        result = await self.session.execute(
            query.order_by(DeletedAccount.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        accounts = result.scalars().all()
        
        accounts_data = []
        for account in accounts:
            accounts_data.append({
                "id": str(account.id),
                "main_account": {
                    "url": account.main_account_url,
                    "id": account.main_account_id,
                    "name": account.main_account_name
                },
                "deleted_accounts": account.deleted_accounts_data,
                "created_at": account.created_at.isoformat()
            })
        
        return {
            "accounts": accounts_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
        
    async def add_deleted_accounts(
        self,
        main_account_url: str,
        deleted_accounts: List[Dict],
        current_user: Dict
    ) -> DeletedAccount:
        """Добавить запись об удаленных аккаунтах"""
        
        new_account = DeletedAccount(
            main_account_url=main_account_url,
            main_account_id=deleted_accounts[0]['id'], 
            main_account_name=deleted_accounts[0]['name'],  
            deleted_accounts_data=deleted_accounts,
            created_by=current_user["id"]
        )
        
        self.session.add(new_account)
        await self.session.commit()
        await self.session.refresh(new_account)
        
        return new_account
    
    async def get_users(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None
    ) -> dict:
        offset = (page - 1) * per_page
        
        query = select(User).join(Role, User.role_id == Role.id)
        
        if search:
            query = query.where(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )
        
        count_query = select(func.count()).select_from(query)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        result = await self.session.execute(
            query.order_by(User.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        users = result.unique().scalars().all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role.name,
                "role_level": user.role.level,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "is_active": user.is_active
            })
        
        return {
            "users": users_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    
    async def get_user_details(self, user_id: uuid.UUID, page: int = 1, per_page: int = 5) -> dict:
        user_result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.unique().scalar()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # История с пагинацией
        history_query = select(UserHistory).where(UserHistory.user_id == user_id)
        history_count = await self.session.execute(select(func.count()).select_from(history_query))
        total_history = history_count.scalar()
        
        history_result = await self.session.execute(
            history_query.order_by(UserHistory.changed_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        history = history_result.unique().scalars().all()
        
        # Обращения с пагинацией
        appeals_query = select(Appeal).where(Appeal.user_id == user_id)
        appeals_count = await self.session.execute(select(func.count()).select_from(appeals_query))
        total_appeals = appeals_count.scalar()
        
        appeals_result = await self.session.execute(
            appeals_query.order_by(Appeal.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        appeals = appeals_result.unique().scalars().all()
        
        # Заявки с пагинацией
        requests_query = select(UserRequest).where(UserRequest.user_id == user_id)
        requests_count = await self.session.execute(select(func.count()).select_from(requests_query))
        total_requests = requests_count.scalar()
        
        requests_result = await self.session.execute(
            requests_query.order_by(UserRequest.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        requests = requests_result.unique().scalars().all()
        
        # Для модераторов - информация о назначенных обращениях с пагинацией
        assigned_appeals = []
        total_assigned = 0
        if user.role.level >= PermissionLevel.JUNIOR_MODERATOR:
            assignments_query = select(AppealAssignment, Appeal).join(
                Appeal, AppealAssignment.appeal_id == Appeal.id
            ).where(AppealAssignment.user_id == user_id)
            
            assigned_count = await self.session.execute(select(func.count()).select_from(assignments_query))
            total_assigned = assigned_count.scalar()
            
            assignments_result = await self.session.execute(
                assignments_query.order_by(AppealAssignment.assigned_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            assigned_appeals = assignments_result.unique().all()
        
        return {
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role.name,
                "role_level": user.role.level,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "is_active": user.is_active,
                "permissions": user.role.permissions
            },
            "history": {
                "items": [{
                    "change_type": h.change_type,
                    "old_value": h.old_value,
                    "new_value": h.new_value,
                    "changed_at": h.changed_at.isoformat(),
                    "changed_by": str(h.changed_by) if h.changed_by else None
                } for h in history],
                "total": total_history,
                "page": page,
                "per_page": per_page
            },
            "appeals": {
                "items": [{
                    "id": str(a.id),
                    "type": a.type.value,
                    "status": a.status.value,
                    "created_at": a.created_at.isoformat()
                } for a in appeals],
                "total": total_appeals,
                "page": page,
                "per_page": per_page
            },
            "requests": {
                "items": [{
                    "id": str(r.id),
                    "request_type": r.request_type,
                    "request_data": r.request_data,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                    "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
                    "resolved_by": str(r.resolved_by) if r.resolved_by else None
                } for r in requests],
                "total": total_requests,
                "page": page,
                "per_page": per_page
            },
            "assigned_appeals": {
                "items": [{
                    "appeal_id": str(a.id),
                    "type": a.type.value,
                    "status": a.status.value,
                    "assigned_at": ass.assigned_at.isoformat(),
                    "released_at": ass.released_at.isoformat() if ass.released_at else None
                } for ass, a in assigned_appeals],
                "total": total_assigned,
                "page": page,
                "per_page": per_page
            }
        }
    
    async def unban_user(self, user_id: uuid.UUID):
        """Разблокировать пользователя"""
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Проверяем, есть ли активный бан
        ban_result = await self.session.execute(
            select(UserBan)
            .where(
                and_(
                    UserBan.user_id == user_id,
                    UserBan.is_active == True,
                    or_(
                        UserBan.expires_at == None,
                        UserBan.expires_at > func.now()
                    )
                )
            )
        )
        active_ban = ban_result.scalar_one_or_none()
        
        if not active_ban:
            raise HTTPException(status_code=400, detail="Пользователь не заблокирован")
        
        # Деактивируем бан
        active_ban.is_active = False
        user.is_active = True
        
        self.session.add(active_ban)
        self.session.add(user)
        await self.session.commit()
        
        history = UserHistory(
            user_id=user_id,
            change_type="ban",
            old_value="Заблокированный",
            new_value="Разблокированный",
        )
        self.session.add(history)
        await self.session.commit()
    
    async def ban_user(
        self,
        user_id: uuid.UUID,
        reason: str,
        banned_by: uuid.UUID,
        ip_address: str,
        user_agent: str
    ):
        """Заблокировать пользователя"""
        from src.utils.fingerprint import generate_fingerprint
        
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        existing_ban = await self.session.execute(
            select(UserBan)
            .where(
                and_(
                    UserBan.user_id == user_id,
                    UserBan.is_active == True,
                    or_(
                        UserBan.expires_at == None,
                        UserBan.expires_at > func.now()
                    )
                )
            )
        )
        if existing_ban.unique().scalar():
            raise HTTPException(status_code=400, detail="Пользователь уже заблокирован")
        
        fingerprint = generate_fingerprint(user_agent, ip_address)
        
        ban = UserBan(
            user_id=user_id,
            reason=reason,
            banned_by=banned_by,
            fingerprint=fingerprint,
            ip_address=ip_address
        )
        
        user.is_active = False
        
        self.session.add(ban)
        self.session.add(user)
        await self.session.commit()
        
        history = UserHistory(
            user_id=user_id,
            change_type="ban",
            old_value="Активный аккаунт",
            new_value=f"banned: {reason}",
            changed_by=banned_by
        )
        self.session.add(history)
        await self.session.commit()
    
    async def get_roles(self, max_level: int) -> List[dict]:
        """Получить список ролей, которые не превышают уровень текущего пользователя"""
        result = await self.session.execute(
            select(Role)
            .where(Role.level <= max_level)
            .order_by(Role.level.desc())
        )
        roles = result.scalars().all()
        
        return [{
            "id": str(role.id),
            "name": role.name,
            "level": role.level,
            "description": role.description
        } for role in roles]
        
    async def change_user_role(
        self,
        user_id: uuid.UUID,
        role_id: str,
        current_user_level: int
    ):
        """Изменить роль пользователя"""
        user = await self.session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        role = await self.session.get(Role, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Роль не найдена")
        
        if role.level > current_user_level:
            raise HTTPException(
                status_code=403,
                detail="Вы не можете назначать роли выше вашего уровня"
            )
        
        user.role_id = role.id
        self.session.add(user)
        await self.session.commit()
        
        # Записываем в историю
        history = UserHistory(
            user_id=user_id,
            change_type="role",
            old_value=str(user.role.name),
            new_value=str(role.name)
        )
        self.session.add(history)
        await self.session.commit()
    
    async def get_pending_requests(self, page: int = 1, per_page: int = 20) -> dict:
        offset = (page - 1) * per_page
        
        query = select(UserRequest).where(UserRequest.status == 'pending')
        
        count_query = select(func.count()).select_from(query)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        result = await self.session.execute(
            query.order_by(UserRequest.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        requests = result.scalars().all()
        
        requests_data = []
        for request in requests:
            user_result = await self.session.execute(
                select(User).where(User.id == request.user_id)
            )
            user = user_result.unique().scalar()
            
            requests_data.append({
                "id": str(request.id),
                "user_id": str(request.user_id),
                "user_name": user.username if user else "Unknown",
                "request_type": request.request_type,
                "request_data": request.request_data,
                "created_at": request.created_at.isoformat(),
                "status": request.status
            })
        
        return {
            "requests": requests_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }

    async def process_request(
        self,
        request_id: uuid.UUID,
        action: str, 
        resolved_by: uuid.UUID
    ) -> bool:
        request = await self.session.get(UserRequest, request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Заявка от пользователя не найдена")
        
        if request.status != 'pending':
            raise HTTPException(status_code=400, detail="Заявку уже обрабатывает другой модератор")
        
        request.status = 'approved' if action == 'approve' else 'rejected'
        request.resolved_at = func.now()
        request.resolved_by = resolved_by
        
        if action == 'approve' and request.request_type == UserRequestType.USERNAME_CHANGE:
            user = await self.session.get(User, request.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="пользователь не найден")
            
            new_username = request.request_data.get('new_username')
            if not new_username:
                raise HTTPException(status_code=400, detail="Некорректный ник в заявки от пользователя")
            
            user.username = new_username
            self.session.add(user)
            
            history = UserHistory(
                user_id=user.id,
                change_type="username",
                old_value=request.request_data.get('old_username', ''),
                new_value=new_username,
                changed_by=resolved_by
            )
            self.session.add(history)
        
        elif action == 'approve' and request.request_type == UserRequestType.ACCOUNT_DELETION:
            user = await self.session.get(User, request.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            
            user.is_active = False
            self.session.add(user)
            
            history = UserHistory(
                user_id=user.id,
                change_type="account_deletion",
                old_value="Active",
                new_value="Deleted",
                changed_by=resolved_by
            )
            self.session.add(history)
        
        self.session.add(request)
        await self.session.commit()
        
        return True
    
    async def get_moderators_list(self) -> List[dict]:
        """Получить список всех модераторов"""
        result = await self.session.execute(
            select(User)
            .join(Role, User.role_id == Role.id)
            .where(Role.level >= PermissionLevel.JUNIOR_MODERATOR)
            .order_by(Role.level.desc(), User.username)
        )
        
        moderators = result.unique().scalars().all()
        
        return [{
            "id": str(moderator.id),
            "username": moderator.username,
            "role_level": moderator.role.level,
            "role_name": moderator.role.name
        } for moderator in moderators]
    
async def get_admin_service(session: AsyncSession = Depends(get_session)) -> AdminService:
    return AdminService(session)