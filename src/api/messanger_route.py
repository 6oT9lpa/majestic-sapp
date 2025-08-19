from src.utils.security import SecurityUtils
from src.services.appeal_service import AppealService, get_appeal_service
from src.services.auth_handler import get_current_user_websoket, get_current_user, get_username_by_id
from src.models.role_model import PermissionLevel
from src.security_middleware import AppealPermissionChecker
from src.services.messanger_service import MessangerService, get_messager_service
from src.websoket import manager
from src.security_middleware import RoleLevelChecker
from src.utils.log import log_action, log_action_ws, ActionType

from fastapi import WebSocket, WebSocketDisconnect, Request, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends
from http.cookies import SimpleCookie
from typing import Dict, List, Optional
from pathlib import Path
import uuid, json, asyncio

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_PATH = PROJECT_ROOT / "storage/files"

router = APIRouter()

@router.websocket("/appeals/{appeal_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    appeal_id: str,
    appeal_service: AppealService = Depends(get_appeal_service),
    messanger_service: MessangerService = Depends(get_messager_service),
):
    await websocket.accept()
    
    try:
        cookie_header = websocket.headers.get("cookie")
        if not cookie_header:
            await websocket.close(code=1008, reason="Токен не найден")
            return
            
        cookies = SimpleCookie()
        cookies.load(cookie_header)
        token = cookies.get("access_token")
        if not token:
            await websocket.close(code=1008, reason="Токен не найден")
            return

        user = await get_current_user_websoket(token.value)
        if not user:
            await websocket.close(code=1008, reason="Пользователь не найден")
            return

        try:
            appeal = await appeal_service.get_appeal_by_id(uuid.UUID(appeal_id))
            if not appeal:
                await websocket.close(code=1008, reason="Обращение не найдено")
                return
        except ValueError:
            await websocket.close(code=1008, reason="Неверный ID обращения")
            return

        is_appeal_owner = user["id"] == appeal["user_id"]
        is_moderator = SecurityUtils.has_role_or_higher(user, PermissionLevel.JUNIOR_MODERATOR)
        
        if not is_appeal_owner and not is_moderator:
            await websocket.close(code=1008, reason="Доступ запрещен")
            return
        
        if is_moderator:
            if appeal["assigned_moder_id"] != user["id"]: 
                allowed_types = AppealPermissionChecker.get_allowed_appeal_types(user)
                if appeal["type"] not in allowed_types:
                    await websocket.close(code=1008, reason="Нет прав на этот тип обращений")
                    return
                
                allowed_statuses = AppealPermissionChecker.get_allowed_statuses(user, appeal["type"])
                if appeal["status"] not in allowed_statuses:
                    await websocket.close(code=1008, reason="Нет прав для текущего статуса обращения")
                    return
                
        if is_moderator and appeal["status"] == "pending":
            can_reassign = await SecurityUtils.can_reassign_appeal(
                user_id=user["id"],
                appeal_id=uuid.UUID(appeal_id),
            )
            
            if not can_reassign:
                await websocket.close(code=1008, reason="Вы не можете повторно взять это обращение")
                return

        await manager.connect(appeal_id, websocket)
        
        try:
            while True:
                data = await websocket.receive_json()
                
                updated_appeal = await appeal_service.get_appeal_by_id(uuid.UUID(appeal_id))
                if updated_appeal["status"] not in ["pending", "in_progress"]:
                    await websocket.send_json({
                        "error": "Обращение закрыто. Вы не можете отправлять сообщения."
                    })
                    continue
                
                # Проверка частоты сообщений
                if not manager.can_send_message(appeal_id, str(user["id"])):
                    await websocket.send_json({
                        "error": "Слишком частые сообщения. Пожалуйста, подождите."
                    })
                    continue
                
                if not isinstance(data.get("message"), str) or len(data["message"]) > 1500:
                    await websocket.send_json({
                        "error": "Недопустимое сообщение"
                    })
                    continue
                
                # Проверка прав на отправку сообщений
                if not SecurityUtils.can_send_messages(
                    user, 
                    appeal["type"], 
                    appeal["status"], 
                    appeal["assigned_moder_id"] == user["id"],
                    is_moderator,
                    is_appeal_owner
                ):
                    await websocket.send_json({
                        "error": "Вы не можете отправлять сообщения в это обращение"
                    })
                    continue
                
                # Обновляем статус обращения для модератора
                if is_moderator and appeal["status"] == "pending":
                    await messanger_service.update_appeal_status(
                        appeal_id=appeal_id,
                        new_status="in_progress",
                        assigned_to=user["id"]
                    )
                    appeal["status"] = "in_progress"
                    appeal["assigned_moder_id"] = user["id"]
                    appeal["assigned_moder_name"] = user["username"]
                    
                    system_message = await messanger_service.save_appeal_message(
                        appeal_id=appeal_id,
                        user_id=user["id"],
                        message="Обращение взято в работу",
                        is_system=True
                    )
                    await manager.send_message(appeal_id, {
                        "id": str(system_message["id"]),
                        "appeal_id": appeal_id,
                        "user_id": str(user["id"]),
                        "message": system_message["message"],
                        "is_system": True,
                        "created_at": system_message["created_at"],
                        "user_name": user.get("username", "Администратор")
                    })
                    
                    await log_action_ws(
                        websocket=websocket,
                        action_type=ActionType.appeal_progress,
                        action_data=f"Пользователь {user["username"]} взял в работу обращение ID: {appeal_id}",
                        user_id=user["id"]
                    )
                
                attachment_ids = data.get("attachment_ids", [])
            
                # Сохраняем и отправляем сообщение
                message = await messanger_service.save_appeal_message(
                    appeal_id=appeal_id,
                    user_id=user["id"],
                    message=data["message"],
                    is_system=False,
                    attachment_ids=attachment_ids 
                )
                
                await manager.send_message(appeal_id, {
                    "id": str(message["id"]),
                    "appeal_id": appeal_id,
                    "user_id": str(user["id"]),
                    "message": message["message"],
                    "is_system": False,
                    "created_at": message["created_at"],
                    "user_name": user.get("username", "Администратор"),
                    "attachments": attachment_ids 
                })
                
        except WebSocketDisconnect:
            manager.disconnect(appeal_id, websocket)
        except json.JSONDecodeError:
            await websocket.close(code=1003, reason="Неверный формат данных")
        except Exception as e:
            await websocket.close(code=1011, reason=f"Internal server error {str(e)}")
        finally:
            manager.disconnect(appeal_id, websocket)
                        
    except Exception as e:
        try:
            await websocket.close(code=1011, reason=f"Internal server error {str(e)}")
        finally:
            manager.disconnect(appeal_id)

@router.post("/appeals/{appeal_id}/upload", dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def upload_files(
    appeal_id: uuid.UUID,
    files: List[UploadFile],
    messanger_service: MessangerService = Depends(get_messager_service),
    user: dict = Depends(get_current_user)
):
    """Загрузить файлы для обращения"""
    try:
        attachments = await messanger_service.save_attachments(
            files=files,
            appeal_id=appeal_id,
            user_id=user["id"]
        )
        return {"attachments": attachments}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/appeals/{appeal_id}/files/{file_name}", dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def get_file(
    appeal_id: uuid.UUID,
    file_name: str,
    messanger_service: MessangerService = Depends(get_messager_service)
):
    """Получить файл обращения"""
    file_path = STORAGE_PATH / str(appeal_id) / file_name
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(file_path)

@router.get("/appeals/{appeal_id}/chat", dependencies=[Depends(RoleLevelChecker(PermissionLevel.USER))])
async def get_appeal_chat(
    request: Request,
    appeal_id: uuid.UUID,
    messanger_service: MessangerService = Depends(get_messager_service),
    appeals_service: AppealService = Depends(get_appeal_service)
):
    """Получение полных данных обращения"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    appeal = await appeals_service.get_appeal_by_id(appeal_id)
    if not appeal:
        raise HTTPException(status_code=404, detail="Обращение не найдено")
    
    await check_appeal_access(user, appeal)
    
    can_send = False
    if user["id"] == appeal["user_id"] and appeal["status"] not in ["resolved", "rejerect"]:
        can_send = True 
    else:
        is_moderator = SecurityUtils.has_role_or_higher(user, PermissionLevel.JUNIOR_MODERATOR)
        
        if is_moderator:
            assigned_to_me = appeal.get("assigned_moder_id") == user["id"]
            
            if assigned_to_me and appeal["status"] not in ["resolved", "rejected"]:
                can_send = True
                
            elif appeal["status"] == "pending":
                can_send = SecurityUtils.can_send_messages(
                    user,
                    appeal["type"],
                    appeal["status"],
                    is_assigned=False,
                    is_moderator=True,
                    is_appeal_owner=False
                )
            
            if can_send:
                can_reassign = await SecurityUtils.can_reassign_appeal(
                    user["id"],
                    appeal["id"]
                )
                can_send = can_send and can_reassign
    
    messages = await messanger_service.get_appeal_messages(appeal_id)
    attachments_info = await messanger_service.get_attachments_info(appeal_id)

    formatted_messages = []
    for msg in messages:
        username = await get_username_by_id(msg["user_id"])
        message_data = {
            **msg,
            "username": username
        }
        if msg.get("message_metadata") and "attachments" in msg["message_metadata"]:
            message_data["attachments"] = [
                att_name for att_name in msg["message_metadata"]["attachments"]
                if any(att["name"] == att_name for att in attachments_info)
            ]

        formatted_messages.append(message_data)

    return {
        "appeal": appeal,
        "messages": formatted_messages,
        "can_send_messages": can_send,
        "attachments": attachments_info
    }

@router.post("/appeals/{appeal_id}/close", dependencies=[Depends(RoleLevelChecker(PermissionLevel.JUNIOR_MODERATOR))])
async def close_appeal(
    request: Request,
    appeal_id: uuid.UUID,
    data: dict,
    messanger_service: MessangerService = Depends(get_messager_service)
):
    """Закрыть обращение"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    if not SecurityUtils.has_role_or_higher(user, PermissionLevel.JUNIOR_MODERATOR):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    try:
        await messanger_service.close_appeal(
            appeal_id=appeal_id,
            status=data.get("status", "resolved")
        )
        
        status_message = "Обращение закрыто" if data.get("status") == "resolved" else "Обращение отклонено"
        await messanger_service.save_appeal_message(
            appeal_id=appeal_id,
            user_id=user["id"],
            message=status_message,
            is_system=True
        )
        
        await log_action(
            request=request,
            action_type=ActionType.appeal_closed,
            action_data=f"Пользователь {user["username"]} закрыл обращение ID: {appeal_id}",
            user_id=user["id"]
        )
        
        return {"detail": "Обращение закрыто"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/appeals/{appeal_id}/reassign", dependencies=[Depends(RoleLevelChecker(PermissionLevel.JUNIOR_MODERATOR))])
async def reassign_appeal(
    request: Request,
    appeal_id: uuid.UUID,
    data: dict,
    messanger_service: MessangerService = Depends(get_messager_service)
):
    """Переназначить обращение"""
    user = await get_current_user(request)
    
    try:
        await messanger_service.reassign_appeal(
            appeal_id=appeal_id,
            reassign_type=data.get("reassign_type"),
            current_user_id=user["id"]
        )
        
        await log_action(
            request=request,
            action_type=ActionType.reassigning_appeal,
            action_data=f"Пользователь {user["username"]} снялся с обращения ID: {appeal_id}",
            user_id=user["id"]
        )
        
        return {"detail": "Обращение переназначено"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
async def check_appeal_access(
    user: Dict,
    appeal: Dict,
):
    """Проверка доступа к обращению"""

    if user["id"] == appeal["user_id"]:
        return {"detail": "Доступ разрешен"}
    
    if appeal["status"] == "in_progress":
        if appeal.get("assigned_moder_id") == user["id"]:
            return {"detail": "Доступ разрешен"}
        
        if not SecurityUtils.has_permission_by_name(user, "view_active_chats"):
            raise HTTPException(status_code=403, detail="Обращение назначено другому пользователю")

    allowed_types = AppealPermissionChecker.get_allowed_appeal_types(user)
    if appeal["type"] not in allowed_types:
        raise HTTPException(status_code=403, detail="Нет прав для просмотра этого обращения")

    allowed_statuses = AppealPermissionChecker.get_allowed_statuses(user, appeal["type"])
    if appeal["status"] not in allowed_statuses:
        raise HTTPException(status_code=403, detail="Нет прав для просмотра обращения с этим статусом")

    return {"detail": "Доступ разрешен"}