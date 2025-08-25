from fastapi import Request, HTTPException, WebSocket
from typing import Optional
from enum import Enum
import uuid

from src.models.user_model import UserActionLog
from src.database import get_session

class ActionType(str, Enum):
    create_appeal = "create_appeal"                             # Создание обращений +
    appeal_progress = "appeal_progress"                         # Обращение на рассмотрении +
    appeal_closed = "appeal_closed"                             # Обращение закрыто +
    register_user = "register_user"                             # Регистрация нового пользователя +
    user_login = "user_login"                                   # Вход пользователя +
    update_role_user = "update_role_user"                       # Изменение уровня доступа +
    account_deletion_requested = "account_deletion_requested"   # Запрос на удаление аккаунта +
    delete_account = "delete_account"                           # Удаление аккаунта +
    add_account_deletion = "add_account_deletio"                # Учет удаленных аккаунтов +
    update_stats_user = "update_stats_user"                     # Изменение статистики пользователя +
    reassigning_appeal = "reassigning_appeal"                   # Переназнаечние на обращении +
    banned_user = "banned_user"                                 # Блокировка аккаунта +
    unbanned_user = "unbanned_user"                             # Разблокировка аккаунта + 
    approved_request = "approved_request"                       # Обобрение заявки +
    rejected_request = "rejected_request"                       # Отклонение заявки +
    password_changed = "password_changed"                       # Смена пароля +
    username_change_request = "username_change_request"         # Запрос на смену ника +
    upload_reports = "upload_reports"                           # Загрузка отчетов +

async def log_action (
    request: Request,
    action_type: ActionType,
    action_data: dict,
    user_id: Optional[uuid.UUID]
):
    
    ip = request.headers.get('X-Forwarded-For', request.client.host)
    user_agent = request.headers.get('User-Agent')
    
    async for session in get_session():
        try: 
            log_entry = UserActionLog(
                user_id=user_id,
                action_type=action_type,
                action_details=action_data,
                ip_address=ip.split(',')[0].strip(),
                user_agent=user_agent
            )
            session.add(log_entry)
            await session.commit()
        
        except HTTPException:
            raise
        except Exception:
            await session.rollback()
            raise HTTPException(status_code=500, detail="Произошла серверная ошибка, обратитесь к разработчику!")

async def log_action_ws(
    websocket: WebSocket,
    action_type: ActionType,
    action_data: dict,
    user_id: Optional[uuid.UUID]
):
    ip = websocket.headers.get('X-Forwarded-For') or websocket.client.host
    user_agent = websocket.headers.get('User-Agent')

    async for session in get_session():
        try:
            log_entry = UserActionLog(
                user_id=user_id,
                action_type=action_type,
                action_details=action_data,
                ip_address=ip.split(',')[0].strip() if isinstance(ip, str) else str(ip),
                user_agent=user_agent
            )
            session.add(log_entry)
            await session.commit()

        except HTTPException:
            raise
        except Exception:
            await session.rollback()
            raise HTTPException(status_code=500, detail="Произошла серверная ошибка, обратитесь к разработчику!")