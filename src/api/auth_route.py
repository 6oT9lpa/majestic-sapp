from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
import urllib.parse

from src.schemas.user_schema import UserCreate, UserLogin
from src.services.auth_service import AuthService, get_auth_service
from src.services.auth_handler import set_auth_cookies, get_current_user, clear_auth_cookies
from src.models.user_model import User
from src.utils.log import log_action, ActionType

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.post("/login")
async def login(
    request: Request,
    user_data: UserLogin, 
    auth_service: AuthService = Depends(get_auth_service),
    response: Response = None
):
    result = await auth_service.authenticate_user(user_data)
    set_auth_cookies(response, result["tokens"])
    
    await log_action(
        request=request,
        action_type=ActionType.user_login,
        action_data=f"Пользователь {result["user"].username} вошел в систему",
        user_id=result["user"].id
    )
    
    return {"message": "Успешный вход"}

@router.post("/register")
async def register(
    user_data: UserCreate, 
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
):
    
    await auth_service.register_user(user_data, background_tasks)
    return {"message": "На вашу почту отправлено письмо с подтверждением"}

@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен истек, войдите в аккаунт снова!"
        )
    
    try:
        tokens = await auth_service.refresh_access_token(refresh_token)
        set_auth_cookies(response, tokens)
        return {"message": "Токены были востановлены"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Токен не найден, войдите в систему снова!"
        )

@router.get("/verify-email")
async def verify_email(
    request: Request, 
    token: str, 
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        result = await auth_service.verify_email(token)
        
        await log_action(
            request=request,
            action_type=ActionType.register_user,
            action_data=f"Пользователь {result['user'].username} зарегистрировался",
            user_id=result["user"].id
        )
        
        response = RedirectResponse(url="/?verify=success")
        set_auth_cookies(response, result["tokens"])
        return response
        
    except HTTPException as e:
        error_msg = urllib.parse.quote(e.detail)
        return RedirectResponse(url=f"/?verify=error&message={error_msg}")

@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "Вы вышли с аккаунта"}

@router.get("/get-user")
async def get_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    return user

@router.post("/check-user")
async def check_user_exist(
    user_data: dict,
    auth_service: AuthService = Depends(get_auth_service)
):
    existing_user = await auth_service.session.execute(
        select(User).where(
            (User.username == user_data.get("username")) |
            (User.email == user_data.get("email"))
        )
    )
    return {"exists": existing_user.scalars().first() is not None}