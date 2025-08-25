from datetime import datetime
from pathlib import Path
import json
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, Form, Request
from fastapi.templating import Jinja2Templates
from typing import Dict, Optional, List

from src.models.appeal_model import AppealStatus, AppealType
from src.security_middleware import RoleLevelChecker, PermissionLevel
from src.services.auth_handler import get_current_user
from src.services.reports_service import ReportService, get_report_service
from src.schemas.user_stats_schema import UserStatsResponse, UserStatsUpdate
from src.utils.log import log_action, ActionType

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMPLAINT_DIR = PROJECT_ROOT / "storage/complaint"

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

@router.post("/upload-reports", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))])
async def upload_reports(
    request: Request,
    reports_file: UploadFile,
    file_content: str = Form(None),
    report_service: ReportService = Depends(get_report_service)
):
    """Загрузка JSON файла с отчетами"""
    try:
        user = await get_current_user(request)
        
        if not reports_file.filename.lower().endswith('.json'):
            raise HTTPException(status_code=400, detail="Файл должен быть в формате JSON")
        
        if file_content:
            content = file_content
        else:
            content = await reports_file.read()
            content = content.decode('utf-8')
        
        try:
            reports_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Некорректный JSON формат: {str(e)}")
        
        if not isinstance(reports_data, list):
            raise HTTPException(status_code=400, detail="Файл должен содержать массив отчетов")
        
        if reports_data:
            first_report = reports_data[0]
            required_fields = ['staff', 'status', 'startDate', 'endDate', 'reportDate', 'link', 'report_id']
            
            for field in required_fields:
                if field not in first_report:
                    raise HTTPException(status_code=400, detail=f"Отсутствует обязательное поле: {field}")
        
        current_date = datetime.now().strftime("%d%m%Y")
        filename = f"{current_date}_reports.json"
        file_path = COMPLAINT_DIR / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(reports_data, f, indent=2, ensure_ascii=False)
        
        await log_action(
            request=request,
            action_type=ActionType.upload_reports,
            action_data=f"Пользователь {user['username']} загрузил новые отчеты из файла {reports_file.filename}",
            user_id=user["id"]
        )
        
        return {"message": "Отчеты успешно загружены", "filename": filename}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке отчетов: {str(e)}")