from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder

from src.services.auth_handler import get_current_user

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