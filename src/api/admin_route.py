from fastapi import APIRouter, Depends, Request, HTTPException, Query, Form
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from typing import List, Optional
import json
import uuid

from src.utils.security import SecurityUtils
from src.models.appeal_model import AppealStatus, AppealType
from src.security_middleware import RoleLevelChecker, AppealPermissionChecker, PermissionLevel
from src.services.auth_handler import get_current_user
from src.services.admin_service import AdminService, get_admin_service
from src.schemas.dashboard_schema import ForumUrlSchema
from src.services.logs_service import LogService, get_log_service
from src.utils.log import log_action, ActionType

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", dependencies=[Depends(RoleLevelChecker(PermissionLevel.JUNIOR_MODERATOR))])
async def get_admin_dashboard(request: Request):
    """Главная страница админ-панели"""
    user = await get_current_user(request)
    
    return templates.TemplateResponse("admin-dashboard.html", {
        "request": request,
        "user": jsonable_encoder(user)
    })

@router.get("/appeals", dependencies=[Depends(AppealPermissionChecker())])
async def get_appeals(
    request: Request,
    status: List[AppealStatus] = Query(...),
    type: Optional[AppealType] = None,
    assigned_to_me: Optional[bool] = None,
    page: int = 1,
    per_page: int = 5,
    search: Optional[str] = None,  # Добавляем параметр поиска
    admin_service: AdminService = Depends(get_admin_service)
):
    """Получить список обращений с фильтрацией согласно правам пользователя"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    if assigned_to_me:
        return await admin_service.get_appeals(
            current_user=user,
            status=status,
            type=type if type else None,
            assigned_to_me=assigned_to_me,
            page=page,
            per_page=per_page,
            search=search
        )

    # Фильтрация по разрешенным типам обращений
    allowed_types = AppealPermissionChecker.get_allowed_appeal_types(user)
    if not allowed_types:
        raise HTTPException(status_code=403, detail="Нет прав для просмотра обращений")

    if type and type.value not in allowed_types:
        raise HTTPException(status_code=403, detail=f"Нет прав для просмотра обращений типа {type.value}")

    # Фильтрация по разрешенным статусам
    filtered_statuses = []
    for s in status:
        if type:
            allowed_for_type = AppealPermissionChecker.get_allowed_statuses(user, type.value)
        else:
            # Если тип не указан, проверяем для всех разрешенных типов
            allowed_for_type = []
            for t in allowed_types:
                allowed_for_type.extend(AppealPermissionChecker.get_allowed_statuses(user, t))
            allowed_for_type = list(set(allowed_for_type))
        
        if s.value in allowed_for_type:
            filtered_statuses.append(s)

    if not filtered_statuses:
        raise HTTPException(status_code=403, detail="Нет прав для просмотра обращений с указанными статусами")

    return await admin_service.get_appeals(
        current_user=user,
        status=filtered_statuses,
        type=type if type else None,
        assigned_to_me=assigned_to_me,
        page=page,
        per_page=per_page,
        search=search
    )

@router.get("/appeals/{appeal_id}/support-moderator", dependencies=[Depends(RoleLevelChecker(PermissionLevel.JUNIOR_MODERATOR))])
async def get_support_moderator(
    request: Request,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Получить закрепленного модератора и его команду саппортов"""
    user = await get_current_user(request)
    
    if not SecurityUtils.has_role_or_higher(user, PermissionLevel.JUNIOR_MODERATOR):
        raise HTTPException(status_code=403, detail="Вы не модератор")
    
    moderator_info = await admin_service.get_support_moderator(user["id"])
    
    if not moderator_info:
        raise HTTPException(status_code=404, detail="Закрепленный модератор не найден")
    
    return moderator_info

@router.get("/deleted-accounts", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def get_deleted_accounts(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Получить список удаленных аккаунтов"""
    return await admin_service.get_deleted_accounts(page=page, per_page=per_page)

@router.post("/deleted-accounts", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def add_deleted_accounts(
    request: Request,
    main_account_url: str = Form(...),
    deleted_accounts: str = Form(...), 
    admin_service: AdminService = Depends(get_admin_service)
):
    """Добавить запись об удаленных аккаунтах"""
    
    try:
        # Валидация основной ссылки
        main_account = ForumUrlSchema(url=main_account_url)
        
        # Валидация удаляемых аккаунтов
        deleted_accounts_list = json.loads(deleted_accounts)
        validated_accounts = []
        for account in deleted_accounts_list:
            validated = ForumUrlSchema(url=account['url'])
            validated_accounts.append({
                "url": validated.url,
                "name": validated.username,
                "id": validated.user_id
            })
            
        user = await get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Не авторизован")
        
        await admin_service.add_deleted_accounts(
            main_account_url=main_account.url,
            deleted_accounts=validated_accounts,
            current_user=user
        )
        
        await log_action(
            request=request,
            action_type=ActionType.add_account_deletion,
            action_data = (
                f"Пользователь {user['username']} добавил в лог удаленных аккаунтов "
                f"ID ACCOUNT: {[acc['id'] for acc in validated_accounts]}"
            ),
            user_id=user["id"]
        )
        
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Некорректный формат данных")

@router.get("/general", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR_SUPERVISOR))])
async def get_general(request: Request):
    user = await get_current_user(request)
    
    return templates.TemplateResponse("admin-general.html", {
        "request": request,
        "user": jsonable_encoder(user)
    })

@router.get("/general/logs", dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def get_logs(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    action_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None), 
    log_service: LogService = Depends(get_log_service)
):
    user_uuid = None
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Некорректный ID пользователя")
    
    return await log_service.get_logs(
        page=page,
        per_page=per_page,
        action_type=action_type,
        user_id=user_uuid,
        search_query=search
    )

@router.get("/general/users", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def get_users(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Получить список пользователей"""
    
    return await admin_service.get_users(
        page=page,
        per_page=per_page,
        search=search
    )

@router.get("/general/users/{user_id}", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def get_user_details(
    request: Request,
    user_id: uuid.UUID,
    page: int = Query(1, gt=0),
    per_page: int = Query(5, gt=0),
    admin_service: AdminService = Depends(get_admin_service)
):
    return await admin_service.get_user_details(user_id, page=page, per_page=per_page)

@router.post("/general/users/{user_id}/ban", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def ban_user(
    request: Request,
    user_id: uuid.UUID,
    reason: str,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Заблокировать пользователя"""
    current_user = await get_current_user(request)
    
    if current_user["id"] == user_id: 
        return HTTPException(
            status_code=400,
            detail="Вы не можете себя заблокировать"
        )
    
    ip = request.headers.get('X-Forwarded-For', request.client.host)
    user_agent = request.headers.get('User-Agent')
    
    await admin_service.ban_user(
        user_id=user_id,
        reason=reason,
        banned_by=current_user["id"],
        ip_address=ip,
        user_agent=user_agent
    )
    
    await log_action(
        request=request,
        action_type=ActionType.banned_user,
        action_data = (
            f"Пользователь {current_user['username']} заблокировал аккаунт с ID: {user_id} с причиной: {reason}"
        ),
        user_id=current_user["id"]
    )
    return {"message": "Пользователь был заблокирован"}

@router.get("/general/roles", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def get_roles_list(
    request: Request,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Получить список ролей"""
    current_user = await get_current_user(request)
    
    return await admin_service.get_roles(current_user["role"]["level"])

@router.post("/general/users/{user_id}/unban", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def unban_user(
    request: Request,
    user_id: uuid.UUID,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Разблокировать пользователя"""
    current_user = await get_current_user(request)
    
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Вы не можете разблокировать себя")
    
    await admin_service.unban_user(user_id)
    
    await log_action(
        request=request,
        action_type=ActionType.unbanned_user,
        action_data = (
            f"Пользователь {current_user['username']} разблокировал аккаунт с ID: {user_id}"
        ),
        user_id=current_user["id"]
    )
    
    return {"message": "Пользователь был разблокирован"}

@router.post("/general/users/{user_id}/role", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def change_user_role(
    request: Request,
    user_id: uuid.UUID,
    role_id: str,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Изменить роль пользователя"""
    current_user = await get_current_user(request)
    
    await admin_service.change_user_role(
        user_id=user_id,
        role_id=role_id,
        current_user_level=current_user["role"]["level"]
    )
    
    await log_action(
        request=request,
        action_type=ActionType.update_role_user,
        action_data = (
            f"Пользователь {current_user['username']} изменил уровень доступа аккаунту с ID: {user_id}"
        ),
        user_id=current_user["id"]
    )
    
    return {"message": "Уровень доступа для пользователя был изменен!"}

@router.get("/general/requests", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def get_pending_requests(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Получить список ожидающих заявок"""
    return await admin_service.get_pending_requests(page=page, per_page=per_page)

@router.post("/general/requests/{request_id}/approve", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def approve_request(
    request: Request,
    request_id: uuid.UUID,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Одобрить заявку"""
    user = await get_current_user(request)
    await admin_service.process_request(request_id, 'approve', user["id"])
    
    await log_action(
        request=request,
        action_type=ActionType.approved_request,
        action_data=f"Пользователь {user["username"]} одобрил заявку ID: {request_id}",
        user_id=user["id"]
    )
    
    return {"message": "Заявка была успешно одобренна"}

@router.post("/general/requests/{request_id}/reject", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def reject_request(
    request: Request,
    request_id: uuid.UUID,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Отклонить заявку"""
    user = await get_current_user(request)
    await admin_service.process_request(request_id, 'reject', user["id"])
    
    await log_action(
        request=request,
        action_type=ActionType.rejected_request,
        action_data=f"Пользователь {user["username"]} отклонил заявку ID: {request_id}",
        user_id=user["id"]
    )
    
    return {"message": "Заявка была успешно отклонена"}


