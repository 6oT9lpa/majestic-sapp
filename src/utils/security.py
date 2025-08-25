from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import uuid

from src.models.user_model import UserPermissionOverride
from src.models.role_model import PermissionLevel, PermissionType
from src.models.appeal_model import AppealAssignmentHistory
from src.database import  get_session

class SecurityUtils:
    @staticmethod
    def has_role_or_higher(user: dict, required_level: PermissionLevel) -> bool:
        """Проверяет, что уровень роли пользователя >= требуемого"""
        if not user.get("role"):
            return False
        return user["role"]["level"] >= required_level.value

    @staticmethod
    def check_role_or_higher(user: dict, required_level: PermissionLevel) -> None:
        """Вызывает исключение, если уровень роли недостаточен"""
        if not SecurityUtils.has_role_or_higher(user, required_level):
            raise PermissionError(
                f"Requires at least {required_level.name} role"
            )

    @staticmethod
    def has_permission(user: dict, permission: PermissionType) -> bool:
        """Проверяет конкретное право с учетом переопределений"""
        if not user.get("role"):
            return False

        # Проверяем переопределения прав пользователя
        if user.get("override_permission"):
            override_value = user["override_permission"]["permissions"].get(permission.value[0])
            if override_value is not None:
                return override_value

        # Проверяем права роли
        role = user["role"]
        permissions = role.get("permissions", {})
        
        if permission.value[0] in permissions:
            return permissions[permission.value[0]]
        
        return role["level"] >= permission.value[1].value

    @staticmethod
    def can_view_appeal_type(user: dict, appeal_type: str) -> bool:
        """Проверяет, может ли пользователь видеть обращения данного типа"""
        from src.security_middleware import AppealPermissionChecker
        allowed_types = AppealPermissionChecker.get_allowed_appeal_types(user)
        return appeal_type in allowed_types

    @staticmethod
    def can_view_appeal_status(user: dict, appeal_type: str, appeal_status: str) -> bool:
        """Проверяет, может ли пользователь видеть обращения данного типа и статуса"""
        from src.security_middleware import AppealPermissionChecker
        allowed_statuses = AppealPermissionChecker.get_allowed_statuses(user, appeal_type)
        return appeal_status in allowed_statuses
    
    @staticmethod
    def check_permission(user: dict, permission: PermissionType) -> None:
        """Вызывает исключение, если право отсутствует"""
        if not SecurityUtils.has_permission(user, permission):
            raise PermissionError(f"Missing permission: {permission.value}")
    
    @staticmethod
    def has_permission_by_name(user: dict, permission_name: str) -> bool:
        """Проверяет конкретное право по имени с учетом переопределений"""
        if not user.get("role"):
            return False

        # Сначала проверяем переопределения прав пользователя
        if user.get("override_permission"):
            override_value = user["override_permission"]["permissions"].get(permission_name)
            if override_value is not None:
                return override_value

        # Если переопределения нет, проверяем стандартные права роли
        permissions = user["role"].get("permissions", {})
        return permissions.get(permission_name, False)
    
    @staticmethod
    def can_send_messages(
        user: dict, 
        appeal_type: str, 
        appeal_status: str,
        is_assigned: bool = False,
        is_moderator: bool = False,
        is_appeal_owner: bool = False,
    ) -> bool:
        """Проверяет, может ли пользователь отправлять сообщения для данного обращения"""
        if appeal_status in ["resolved", "rejected"]:
            return False
        
        if is_moderator: 
            if is_assigned and appeal_status == "in_progress":
                return True
            
            if appeal_type == "help":
                return SecurityUtils.has_permission_by_name(user, "respond_support_tickets")
            elif appeal_type == "complaint":
                return SecurityUtils.has_permission_by_name(user, "respond_moderation_complaints")
            elif appeal_type == "amnesty":
                return SecurityUtils.has_permission_by_name(user, "respond_amnesty_requests")
        
        return is_appeal_owner
    
    @staticmethod
    async def can_reassign_appeal(
        user_id: uuid.UUID,
        appeal_id: uuid.UUID,
    ) -> bool:
        """
        Проверяет, может ли пользователь взять обращение повторно
        Возвращает False если пользователь был снят с этого обращения с флагом cannot_reassign
        """
        async for session in get_session():
            result = await session.execute(
                select(AppealAssignmentHistory).where(
                    and_(
                        AppealAssignmentHistory.appeal_id == appeal_id,
                        AppealAssignmentHistory.user_id == user_id,
                        AppealAssignmentHistory.cannot_reassign == True
                    )
                )
            )
            return not bool(result.scalar())

    @staticmethod
    async def check_can_reassign_appeal(
        session: AsyncSession,
        user_id: uuid.UUID,
        appeal_id: uuid.UUID
    ) -> None:
        """
        Проверяет возможность повторного взятия обращения, 
        вызывает PermissionError если взятие запрещено
        """
        if not await SecurityUtils.can_reassign_appeal(session, user_id, appeal_id):
            raise PermissionError("Вы не можете повторно взять это обращение")
        
    @staticmethod
    async def set_permission_override(
        session: AsyncSession,
        user_id: uuid.UUID,
        permission: str,
        value: bool
    ) -> None:
        """Устанавливает переопределение права для пользователя"""
        override = await session.get(UserPermissionOverride, user_id)
        if not override:
            override = UserPermissionOverride(user_id=user_id, permissions={})
            session.add(override)
        
        override.permissions[permission] = value
        override.updated_at = func.now()