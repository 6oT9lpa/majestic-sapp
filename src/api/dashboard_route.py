from webbrowser import get
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from typing import List

from src.services.dashboard_service import DashboardService, get_dashboard_service
from src.schemas.dashboard_schema import (
    UserAppeal,
    StatsResponse,
)
from src.services.auth_handler import get_current_user
from src.security_middleware import RoleLevelChecker, PermissionLevel
from src.schemas.user_schema import ChangePaswRequest, ChangeUsernameRequest
from src.services.auth_service import AuthService, get_auth_service
from src.utils.log import log_action, ActionType


router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def get_dashboard(
    request: Request
):
    user = await get_current_user(request)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": jsonable_encoder(user)
    })

@router.get("/data", dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def get_data(
    request: Request,
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    user = await get_current_user(request)
    is_support = user["role"]["level"] >= PermissionLevel.JUNIOR_MODERATOR.value
    
    activities = await dashboard_service.get_recent_activities(user["id"], is_support)
    
    return {
        "activities": activities,
        "user": user
    }

@router.get("/appeals", response_model=List[UserAppeal], dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def get_user_appeals(
    request: Request,
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    user = await get_current_user(request)
    return await dashboard_service.get_user_appeals(user["id"])

@router.post("/user/change-password", dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def change_password(
    request: Request,
    change_data: ChangePaswRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Изменение пароля пользователя"""
    user = await get_current_user(request)
    
    await auth_service.change_password(change_data, user["id"])
    
    await log_action(
        request=request,
        action_type=ActionType.password_changed,
        action_data=f"Пользователь {user["username"]} изменил пароль",
        user_id=user["id"]
    )
    
    return {"message": "Пароль успешно был изменен"}

@router.post("/user/request-username-change", dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def request_username_change(
    request: Request,
    change_data: ChangeUsernameRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Запрос на изменение ника"""
    user = await get_current_user(request)
    
    await auth_service.change_username(change_data, user["id"])
    
    await log_action(
        request=request,
        action_type=ActionType.username_change_request,
        action_data=f"Пользователь {user["username"]} запросил изменение имени на {change_data.new_username}",
        user_id=user["id"]
    )
    
    return {"message": "Вы успешно подали заявку на изменение ника"}

@router.post("/user/request-account-deletion", response_model=dict)
async def request_account_deletion(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Запрос на удаление аккаунта"""
    user = await get_current_user(request)
    
    # Создание заявки
    await auth_service.account_deletion_request(user_id=user["id"])
    
    await log_action(
        request=request,
        action_type=ActionType.account_deletion_requested,
        action_data=f"Пользователь {user["username"]} запросил удаление аккаунта",
        user_id=user["id"]
    )
    
    return {"message": "Заявка на удаление аккаунта отправлена на рассмотрение"}