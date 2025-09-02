from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder

from src.database import get_session
from src.services.auth_handler import get_current_user, check_user_ban, get_username_by_id, get_current_user_without_ban_check

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def index(request: Request):
    try:
        user = await get_current_user(request)
        if user:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "user": jsonable_encoder(user)
            })
    except HTTPException:
        pass
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": None 
    })
    
@router.get("/blocked")
async def blocked_page(request: Request):
    try:
        user_data = await get_current_user_without_ban_check(request)
        
        if not user_data:
            return RedirectResponse(url="/")
        
        async for session in get_session():
            ban = await check_user_ban(user_data["id"], session)
            
            if not ban:
                return RedirectResponse(url="/")
            
            moderator_username = await get_username_by_id(ban.banned_by)
            
            return templates.TemplateResponse(
                "blocked.html",
                {
                    "request": request,
                    "user": user_data,
                    "ban": ban,
                    "moderator_username": moderator_username or "Система"
                }
            )
            
    except Exception as e:

        return templates.TemplateResponse(
            "blocked.html",
            {
                "request": request,
                "user": None,
                "ban": None,
                "moderator_username": "Система"
            }
        )
    
@router.get("/api/check-ban")
async def check_ban_status(request: Request):
    user = await get_current_user(request, raise_exception=False)
    
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не авторизован")
    
    async for session in get_session():
        ban = await check_user_ban(user["id"], session)
        
        if ban:
            raise HTTPException(status_code=403, detail="Пользователь в бане")
    
    return {"status": "active"}