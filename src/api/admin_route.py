from webbrowser import get
from fastapi import APIRouter, Depends, Request, HTTPException, Query, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from typing import List, Optional
from pathlib import Path
import json
import uuid

from src.services.appeal_service import AppealService, get_appeal_service
from src.utils.security import SecurityUtils
from src.models.appeal_model import AppealStatus, AppealType
from src.security_middleware import RoleLevelChecker, AppealPermissionChecker, PermissionLevel
from src.services.auth_handler import BackgroundTasks, get_current_user
from src.services.admin_service import AdminService, get_admin_service
from src.schemas.dashboard_schema import ForumUrlSchema
from src.services.logs_service import LogService, get_log_service
from src.utils.log import log_action, ActionType
from src.services.messanger_service import MessangerService, get_messager_service
from src.services.multiaccount_service import MultiAccountService, get_multi_account_service

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_PATH = PROJECT_ROOT / "storage/files"
STORAGE_PATH.mkdir(parents=True, exist_ok=True)

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
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_desc"),
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
            search=search,
            sort_by=sort_by
        )

    allowed_types = AppealPermissionChecker.get_allowed_appeal_types(user)
    if not allowed_types:
        raise HTTPException(status_code=403, detail="Нет прав для просмотра обращений")
    
    if type and type.value not in allowed_types:
        raise HTTPException(status_code=403, detail=f"Нет прав для просмотра обращений типа {type.value}")

    filtered_statuses = []
    for s in status:
        if type:
            allowed_for_type = AppealPermissionChecker.get_allowed_statuses(user, type.value)
        else:
            allowed_for_type = []
            for t in allowed_types:
                allowed_for_type.extend(AppealPermissionChecker.get_allowed_statuses(user, t))
            allowed_for_type = list(set(allowed_for_type))
        
        if s.value in allowed_for_type:
            filtered_statuses.append(s)
    
    if not filtered_statuses:
        raise HTTPException(status_code=403, detail="Нет прав для просмотра обращений с указанными статусами")

    effective_type = type if type else None
    if not type:
        allowed_type_objects = [AppealType(t) for t in allowed_types]

    return await admin_service.get_appeals(
        current_user=user,
        status=filtered_statuses,
        type=type if type else None,
        assigned_to_me=assigned_to_me,
        page=page,
        per_page=per_page,
        search=search,
        allowed_types=allowed_types if not type else None,
        sort_by=sort_by 
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
        current_user_level=current_user["role"]["level"],
        current_user_id=current_user["id"]
    )
    
    await log_action(
        request=request,
        action_type=ActionType.update_role_user,
        action_data=(
            f"Пользователь {current_user['username']} изменил уровень доступа аккаунту с ID: {user_id}"
        ),
        user_id=current_user["id"]
    )
    
    return {"message": "Уровень доступа для пользователя был изменен!"}

@router.post("/general/users/{user_id}/restore", dependencies=[Depends(RoleLevelChecker(PermissionLevel.LEAD_ADMINISTRATOR))])
async def restore_user(
    request: Request,
    user_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Восстановить удаленного пользователя (только для админов)"""
    current_user = await get_current_user(request)
    
    result = await admin_service.restore_user(user_id, current_user["id"], background_tasks)
    
    await log_action(
        request=request,
        action_type=ActionType.user_restored,
        action_data=f"Пользователь {current_user['username']} восстановил аккаунт с ID: {user_id}",
        user_id=current_user["id"]
    )
    
    return {
        "message": "Пользователь успешно восстановлен. Email с временными данными отправлен.",
        "temporary_password": result["temporary_password"],
        "user_id": str(user_id),
        "username": result["user"].username,
        "email": result["user"].email
    }
    
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

@router.get("/appeals/counters", dependencies=[Depends(RoleLevelChecker(PermissionLevel.JUNIOR_MODERATOR))])
async def get_appeals_counters(
    request: Request,
    admin_service: AdminService = Depends(get_admin_service)
):
    """Получить счетчики обращений с учетом прав доступа"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    return await admin_service.get_appeals_counters(user)

@router.post("/appeals/{appeal_id}/force-close", dependencies=[Depends(RoleLevelChecker(PermissionLevel.CHIEF_CURATOR))])
async def force_close_appeal(
    request: Request,
    appeal_id: uuid.UUID,
    data: dict,
    appeal_service: AppealService = Depends(get_appeal_service),
    messanger_service: MessangerService = Depends(get_messager_service)
):
    """Принудительно закрыть обращение"""
    user = await get_current_user(request)
    
    if not SecurityUtils.has_role_or_higher(user, PermissionLevel.CHIEF_CURATOR):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    reason = data.get('reason')
    if not reason:
        raise HTTPException(status_code=400, detail="Укажите причину закрытия")
    
    try:
        from src.models.appeal_model import Appeal
        from src.database import get_session
        
        async for session in get_session():
            appeal = await session.get(Appeal, appeal_id)
            
            if not appeal:
                raise HTTPException(status_code=404, detail="Обращение не найдено")
            
            appeal.status = AppealStatus.FORCE_CLOSED
            appeal.closed_at = func.now()
            await session.commit()
            break

        await messanger_service.save_appeal_message(
            appeal_id=appeal_id,
            user_id=user["id"],
            message=f"Обращение принудительно закрыто. Причина: {reason}",
            is_system=True
        )
        
        await log_action(
            request=request,
            action_type=ActionType.appeal_closed,
            action_data=f"Пользователь {user['username']} принудительно закрыл обращение ID: {appeal_id}. Причина: {reason}",
            user_id=user["id"]
        )
        
        return {"detail": "Обращение принудительно закрыто"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/moderators", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR))])
async def get_moderators_list(
    admin_service: AdminService = Depends(get_admin_service)
):
    """Получить список модераторов"""
    return await admin_service.get_moderators_list()

@router.post("/appeals/{appeal_id}/reassign-to", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MODERATOR))])
async def reassign_to_moderator(
    request: Request,
    appeal_id: uuid.UUID,
    moderator_id: str,
    messanger_service: MessangerService = Depends(get_messager_service)
):
    """Переназначить обращение на конкретного модератора"""
    user = await get_current_user(request)
    
    try:
        moderator_uuid = uuid.UUID(moderator_id)
        
        await messanger_service.update_appeal_status(
            appeal_id=appeal_id,
            new_status="in_progress",
            assigned_to=moderator_uuid
        )
        
        await messanger_service.save_appeal_message(
            appeal_id=appeal_id,
            user_id=user["id"],
            message=f"Обращение переназначено на нового модератора",
            is_system=True
        )
        
        await log_action(
            request=request,
            action_type=ActionType.reassigning_appeal,
            action_data=f"Пользователь {user['username']} переназначил обращение ID: {appeal_id} на модератора ID: {moderator_id}",
            user_id=user["id"]
        )
        
        return {"detail": "Обращение переназначено"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@router.get("/multi-accounts", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def get_multi_accounts(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Получить список мультиаккаунтов"""
    return await multiaccount_service.get_multi_accounts(page=page, per_page=per_page)

@router.post("/multi-accounts", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def add_multi_accounts(
    request: Request,
    main_account_url: str = Form(...),
    accounts: str = Form(...),
    comment: Optional[str] = Form(None),
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Добавить запись о мультиаккаунтах"""
    
    try:
        main_account = ForumUrlSchema(url=main_account_url)
        
        # Валидация аккаунтов
        accounts_list = json.loads(accounts)
        validated_accounts = []
        for account in accounts_list:
            validated = ForumUrlSchema(url=account['url'])
            validated_accounts.append({
                "url": validated.url,
                "name": validated.username,
                "id": validated.user_id,
                "type": account.get('type', 'multi') 
            })
            
        user = await get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Не авторизован")
        
        await multiaccount_service.add_multi_accounts(
            main_account_url=main_account.url,
            accounts=validated_accounts,
            comment=comment,
            current_user=user
        )
        
        await log_action(
            request=request,
            action_type=ActionType.add_multi_account,
            action_data=(
                f"Пользователь {user['username']} добавил запись о мультиаккаунтах "
                f"ID ACCOUNTS: {[acc['id'] for acc in validated_accounts]}"
            ),
            user_id=user["id"]
        )
        
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Некорректный формат данных")

@router.get("/multi-accounts/{account_id}", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def get_multi_account_details(
    request: Request,
    account_id: uuid.UUID,
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Получить детальную информацию о мультиаккаунте"""
    return await multiaccount_service.get_multi_account_details(account_id)

@router.post("/multi-accounts/update-account-type", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def update_account_type(
    request: Request,
    data: dict,
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Изменить тип аккаунта (мультиаккаунт/обход блокировки)"""
    try:
        user = await get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Не авторизован")
        
        await multiaccount_service.update_account_type(
            multi_account_id=uuid.UUID(data['multi_account_id']),
            account_id=data['account_id'],
            account_url=data['account_url'],
            new_type=data['new_type'],
            current_user=user
        )
        
        await log_action(
            request=request,
            action_type=ActionType.multi_account_updated,
            action_data=f"Пользователь {user['username']} изменил статус акканта в записи о мультиаккаунтах ID: {data['multi_account_id']}, account_id: {data['account_id']}, статус {data['new_type']}",
            user_id=user["id"]
        )
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/multi-accounts/set-main-account", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def set_main_account(
    request: Request,
    data: dict,
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Установить новый основной аккаунт"""
    try:
        user = await get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Не авторизован")
        
        await multiaccount_service.set_main_account(
            multi_account_id=uuid.UUID(data['multi_account_id']),
            new_main_account_id=data['new_main_account_id'],
            new_main_account_url=data['new_main_account_url'],
            new_main_account_name=data['new_main_account_name'],
            current_user=user
        )
        
        await log_action(
            request=request,
            action_type=ActionType.multi_account_updated,
            action_data=f"Пользователь {user['username']} изменил основной аккаунт в записи о мультиаккаунтах ID: {data['multi_account_id']}, новый основной аккаунт ID: {data['new_main_account_id']}",
            user_id=user["id"]
        )
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/multi-accounts/add-account", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def add_account_to_multi(
    request: Request,
    data: dict,
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Добавить аккаунт к существующей записи мультиаккаунтов"""
    try:
        user = await get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Не авторизован")
        
        await multiaccount_service.add_account_to_multi(
            multi_account_id=uuid.UUID(data['multi_account_id']),
            account_url=data['account_url'],
            account_id=data['account_id'],
            account_name=data['account_name'],
            account_type=data['account_type'],
            current_user=user
        )
        
        await log_action(
            request=request,
            action_type=ActionType.multi_account_updated,
            action_data=f"Пользователь {user['username']} изменил запись о мультиаккаунтах ID: {data['multi_account_id']}, добавлен новый аккаунт ID: {data['account_id']}",
            user_id=user["id"]
        )
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/multi-accounts/{account_id}/comment", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def update_multi_account_comment(
    request: Request,
    account_id: uuid.UUID,
    comment: str = Form(None),
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Обновить комментарий мультиаккаунта"""
    user = await get_current_user(request)
    
    try:
        await multiaccount_service.update_multi_account_comment(
            account_id=account_id,
            comment=comment,
            current_user=user
        )
        
        await log_action(
            request=request,
            action_type=ActionType.multi_account_updated,
            action_data=f"Пользователь {user['username']} изменил запись о мультиаккаунтах ID: {account_id}, обновил комментарий",
            user_id=user["id"]
        )
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/multi-accounts/{account_id}/upload-file", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def upload_multi_account_file(
    request: Request,
    account_id: uuid.UUID,
    file: UploadFile = File(...),
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Загрузить файл для мультиаккаунта"""
    user = await get_current_user(request)
    
    # Проверка типа файла
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Можно загружать только изображения")
    
    max_size = 30 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="Размер файла не должен превышать 30 МБ")
    
    await file.seek(0)
    
    try:
        file_data = await multiaccount_service.upload_multi_account_file(
            account_id=account_id,
            file=file,
            content=content,
            current_user=user
        )
        
        await log_action(
            request=request,
            action_type=ActionType.multi_account_updated,
            action_data=f"Пользователь {user['username']} добавил файл, запись о мультиаккаунтах ID: {account_id}, файл {file.filename}",
            user_id=user["id"]
        )
        
        return {"status": "success", "file": file_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/multi-accounts/{account_id}/files", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def get_multi_account_files(
    account_id: uuid.UUID,
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Получить список файлов мультиаккаунта"""
    try:
        files = await multiaccount_service.get_multi_account_files(account_id)
        return files
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/multi-accounts/{account_id}/files/{file_id}/download", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def download_multi_account_file(
    account_id: uuid.UUID,
    file_id: uuid.UUID,
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Скачать файл мультиаккаунта"""
    try:
        file_path, filename = await multiaccount_service.get_file_path(account_id, file_id)
        
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/multi-accounts/{account_id}/files/{file_id}", dependencies=[Depends(RoleLevelChecker(PermissionLevel.MULTI_ACCOUNT_MODERATOR))])
async def delete_multi_account_file(
    request: Request,
    account_id: uuid.UUID,
    file_id: uuid.UUID,
    multiaccount_service: MultiAccountService = Depends(get_multi_account_service)
):
    """Удалить файл мультиаккаунта"""
    user = await get_current_user(request)
    
    try:
        await multiaccount_service.delete_multi_account_file(
            account_id=account_id,
            file_id=file_id,
            current_user=user
        )
        
        await log_action(
            request=request,
            action_type=ActionType.multi_account_updated,
            action_data=f"Пользователь {user['username']} удалил файл,запись о мультиаккаунтах ID: {account_id}, файл ID: {file_id}",
            user_id=user["id"]
        )
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
