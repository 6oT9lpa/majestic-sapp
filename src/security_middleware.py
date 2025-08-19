from fastapi import Request, HTTPException
from typing import Union, List

from src.utils.security import SecurityUtils
from src.models.role_model import PermissionType, PermissionLevel
from src.services.auth_handler import get_current_user

class BasePermissionChecker:
    async def __call__(self, request: Request):
        try:
            user = await get_current_user(request)
            self.check_access(user)
            request.state.user = user
            return True
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
    
    def check_access(self, user):
        raise NotImplementedError

class PermissionChecker(BasePermissionChecker):
    """Проверяет конкретное разрешение"""
    def __init__(self, permission: PermissionType):
        self.permission = permission
    
    def check_access(self, user):
        SecurityUtils.check_permission(user, self.permission)

class RoleLevelChecker(BasePermissionChecker):
    """Проверяет уровень роли (и все вышестоящие)"""
    def __init__(self, required_level: PermissionLevel):
        self.required_level = required_level
    
    def check_access(self, user):
        SecurityUtils.check_role_or_higher(user, self.required_level)

class CompositePermissionChecker(BasePermissionChecker):
    """Комбинированная проверка прав и уровня роли"""
    def __init__(
        self,
        permission: Union[PermissionType, None] = None,
        role_level: Union[PermissionLevel, None] = None
    ):
        if permission is None and role_level is None:
            raise ValueError("Either permission or role_level must be specified")
        
        self.permission = permission
        self.role_level = role_level
    
    def check_access(self, user):
        if self.role_level:
            SecurityUtils.check_role_or_higher(user, self.role_level)
        if self.permission:
            SecurityUtils.check_permission(user, self.permission)

class AppealPermissionChecker(BasePermissionChecker):
    """Проверяет разрешения для работы с обращениями"""
    def __init__(
        self,
        required_permission: str = None,
        required_level: PermissionLevel = None,
        appeal_type: str = None,
        check_assignment: bool = False
    ):
        self.required_permission = required_permission
        self.required_level = required_level
        self.appeal_type = appeal_type
        self.check_assignment = check_assignment
    
    def check_access(self, user):
        # Проверка уровня роли
        if self.required_level and not SecurityUtils.has_role_or_higher(user, self.required_level):
            raise PermissionError(f"Requires at least {self.required_level.name} role")
        
        # Проверка конкретного разрешения
        if self.required_permission and not SecurityUtils.has_permission_by_name(user, self.required_permission):
            raise PermissionError(f"Missing permission: {self.required_permission}")
        
        # Проверка типа обращения
        if self.appeal_type and self.appeal_type not in self.get_allowed_appeal_types(user):
            raise PermissionError(f"Not allowed to access {self.appeal_type} appeals")

    @staticmethod
    def get_allowed_appeal_types(user: dict) -> List[str]:
        allowed_types = []
        if SecurityUtils.has_permission_by_name(user, "respond_support_tickets"):
            allowed_types.append("help")
        if SecurityUtils.has_permission_by_name(user, "respond_moderation_complaints"):
            allowed_types.append("complaint")
        if SecurityUtils.has_permission_by_name(user, "respond_amnesty_requests"):
            allowed_types.append("amnesty")
            
        return allowed_types

    @staticmethod
    def get_allowed_statuses(user: dict, appeal_type: str) -> List[str]:
        allowed_statuses = []
        
        if appeal_type == "help":
            if SecurityUtils.has_permission_by_name(user, "respond_support_tickets"):
                allowed_statuses.append("pending")
                
            if SecurityUtils.has_permission_by_name(user, "view_active_chats"):
                allowed_statuses.extend(["pending", "in_progress"])
        
        elif appeal_type == "complaint":
            if SecurityUtils.has_permission_by_name(user, "respond_moderation_complaints"):
                allowed_statuses.append("pending")
                
            if SecurityUtils.has_permission_by_name(user, "view_active_chats"):
                allowed_statuses.extend(["pending", "in_progress"])
        
        elif appeal_type == "amnesty":
            if SecurityUtils.has_permission_by_name(user, "respond_amnesty_requests"):
                allowed_statuses.append("pending")
                
            if SecurityUtils.has_permission_by_name(user, "view_active_chats"):
                allowed_statuses.extend(["pending", "in_progress"])
        
        allowed_statuses.extend(["resolved", "rejected"])
        return list(set(allowed_statuses))