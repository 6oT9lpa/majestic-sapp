from fastapi import APIRouter, Depends
from fastapi import Request

from src.schemas.appeal_schema import HelpAppealCreate, ComplaintAppealCreate, AmnestyAppealCreate, AppealResponse
from src.services.appeal_service import AppealService, get_appeal_service
from src.services.auth_handler import get_current_user
from src.models.role_model import PermissionLevel
from src.security_middleware import RoleLevelChecker
from src.utils.log import log_action, ActionType

router = APIRouter()

@router.post("/help", response_model=AppealResponse, dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def create_help_appeal(
    request: Request,
    appeal_data: HelpAppealCreate,
    appeal_service: AppealService = Depends(get_appeal_service)
):
    user = await get_current_user(request)
    
    appeal = await appeal_service.create_appeal(appeal_data, user['id'] if user else None)
    
    await log_action(
        request=request,
        action_type=ActionType.create_appeal,
        action_data=f"Пользователь {user["username"]} создал обращение ID: {appeal.id} *помощь по форуму*",
        user_id=user["id"]
    )
    
    return appeal

@router.post("/complaint", response_model=AppealResponse, dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def create_complaint_appeal(
    request: Request,
    appeal_data: ComplaintAppealCreate,
    appeal_service: AppealService = Depends(get_appeal_service)
):
    user = await get_current_user(request)
    
    appeal = await appeal_service.create_appeal(appeal_data, user['id'] if user else None)
    
    await log_action(
        request=request,
        action_type=ActionType.create_appeal,
        action_data=f"Пользователь {user["username"]} создал обращение ID: {appeal.id} *жалоба на модератора*",
        user_id=user["id"]
    )
    
    return appeal

@router.post("/amnesty", response_model=AppealResponse, dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def create_amnesty_appeal(
    request: Request,
    appeal_data: AmnestyAppealCreate,
    appeal_service: AppealService = Depends(get_appeal_service)
):
    user = await get_current_user(request)
    
    appeal = await appeal_service.create_appeal(appeal_data, user['id'] if user else None)
    
    await log_action(
        request=request,
        action_type=ActionType.create_appeal,
        action_data=f"Пользователь {user["username"]} создал обращение ID: {appeal.id} *обжалования наказания*",
        user_id=user["id"]
    )
    
    return appeal