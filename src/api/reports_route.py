from datetime import datetime
from turtle import st
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from typing import Dict, Optional, List

from src.models.appeal_model import AppealStatus, AppealType
from src.security_middleware import RoleLevelChecker, PermissionLevel
from src.services.auth_handler import get_current_user
from src.scripts.parser_complaint import run_parser_background
from src.services.reports_service import ReportService, get_report_service
from src.schemas.user_stats_schema import UserStatsResponse, UserStatsUpdate
from src.utils.log import log_action, ActionType

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))])
async def get_reports(request: Request):
    """Страница отчетов"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "user": user
    })

@router.get("/complaints", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))])
async def get_complaints(
    request: Request,
    status: str = Query("all"),
    date: str = Query(None),
    admin: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    report_service: ReportService = Depends(get_report_service)
) -> Dict:
    """Получение жалоб с фильтрацией"""
    return await report_service.get_complaints(
        status=status,
        date=date,
        admin=admin,
        page=page,
        per_page=per_page
    )

@router.get("/appeal-stats", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))])
async def get_appeal_stats(
    request: Request,
    status: Optional[List[AppealStatus]] = Query([AppealStatus.IN_PROGRESS, AppealStatus.PENDING, 
                                                AppealStatus.REJECTED, AppealStatus.RESOLVED]),
    appeal_type: Optional[List[AppealType]] = Query([AppealType.AMNESTY, AppealType.COMPLAINT, AppealType.HELP]),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    moderator: Optional[str] = None,
    report_service: ReportService = Depends(get_report_service)
) -> Dict:
    """Получение статистики по обращениям с фильтрацией"""
    
    return await report_service.get_appeal_stats(
        status=status,
        appeal_type=appeal_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
        moderator=moderator
    )

@router.get("/delayed-complaints", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))])
async def get_delayed_complaints(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: str = Query(None),
    report_service: ReportService = Depends(get_report_service)
) -> Dict:
    """Получение просроченных жалоб с поддержкой поиска"""
    return await report_service.get_delayed_complaints(
        page=page,
        per_page=per_page,
        admin=admin
    )

@router.get("/user-stats", dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def get_user_stats(
    request: Request,
    admin_name: str = Query(None),  
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    report_service: ReportService = Depends(get_report_service)
) -> Dict:
    """Получение статистики по пользователям"""
    
    return await report_service.get_user_stats(
        admin_name=admin_name,  
        page=page,
        per_page=per_page
    )

@router.get("/user-activity", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))])
async def get_user_activity(
    request: Request,
    month: int = Query(None, ge=1, le=12),
    year: int = Query(None),
    report_service: ReportService = Depends(get_report_service)
) -> Dict:
    """Получение данных активности пользователей для графика"""
    return await report_service.get_user_activity(
        month=month,
        year=year
    )

@router.post("/update-user-stats", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))], response_model=UserStatsResponse)
async def update_user_stats(
    request: Request,
    stats_data: UserStatsUpdate,
    report_service: ReportService = Depends(get_report_service)
) -> UserStatsResponse:
    try:
        user = await get_current_user(request)
        
        update_data = stats_data.dict(exclude_unset=True)
        username = update_data.pop("username")
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="Не указаны поля для обновления"
            )
        
        result = await report_service.update_user_stats(username, update_data)
        
        await log_action(
            request=request,
            action_type=ActionType.update_stats_user,
            action_data=f"Пользователь {user["username"]} изменил статистику пользователю {username}",
            user_id=user["id"]
        )
        
        return UserStatsResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении статистики: {str(e)}"
        )

@router.get("/reward-settings", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))])
async def get_reward_settings(
    request: Request,
    report_service: ReportService = Depends(get_report_service)
) -> Dict:
    """Получение текущих настроек вознаграждений"""
    return await report_service.get_reward_settings()

@router.post("/update-reward-settings", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))])
async def update_reward_settings(
    request: Request,
    settings_data: Dict,
    report_service: ReportService = Depends(get_report_service)
) -> Dict:
    """Обновление настроек вознаграждений"""
    required_fields = ["complaint_reward", "appeal_reward", "delay_penalty"]
    if not all(field in settings_data for field in required_fields):
        raise HTTPException(
            status_code=400,
            detail="Не указаны все обязательные поля"
        )
    
    # Валидация значений
    for field in required_fields:
        if not isinstance(settings_data[field], int) or settings_data[field] < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Некорректное значение для поля {field}"
            )
    
    return await report_service.update_reward_settings(settings_data)