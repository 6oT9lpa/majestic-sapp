import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.api.main_routes import router as main_router
from src.api.auth_route import router as auth_router
from src.api.appeal_route import router as appel_router
from src.api.dashboard_route import router as dashboard_router
from src.api.admin_route import router as admin_router
from src.api.messanger_route import router as websoket_router
from src.api.reports_route import router as report_router

from src.database import init_db
from src.scripts.init_roles import init_roles
from src.scripts.parser_complaint import run_parser_background, run_parser_for_date

class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        x_forwarded_proto = request.headers.get('x-forwarded-proto')
        x_forwarded_host = request.headers.get('x-forwarded-host')
        
        if x_forwarded_proto == 'https':
            request.scope["scheme"] = "https"
        
        if x_forwarded_host:
            request.scope["host"] = x_forwarded_host
            
        response = await call_next(request)
        return response

def get_application() -> FastAPI:
    application = FastAPI(
        title='FastApi & Majestic',
        debug=False,
        version='0.01'
    )
    
    application.include_router(main_router, tags=['main'])
    application.include_router(auth_router, prefix="/auth", tags=['auth'])
    application.include_router(appel_router, prefix="/appeal", tags=["appeal"])
    application.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
    application.include_router(admin_router, prefix="/dashboard/admin", tags=["dashboard-admin"])
    application.include_router(websoket_router, prefix="/messanger", tags=["messanger"])
    application.include_router(report_router, prefix="/dashboard/admin/reports", tags=["reporting"])

    
    application.add_middleware(ProxyHeadersMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )
    
    application.mount("/static", StaticFiles(directory="static", html=True), name="static")
    application.mount("/storage", StaticFiles(directory="storage"), name="storage")

    
    @application.on_event("startup")
    async def startup():
        await init_db()
        await init_roles()
        pass
        
    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Сохраняем оригинальное сообщение об ошибке
        detail = exc.detail if hasattr(exc, 'detail') else str(exc)
        
        if exc.status_code == 401:
            if "text/html" in request.headers.get("accept", ""):
                return RedirectResponse(url="/")
            return JSONResponse(
                status_code=401,
                content={"detail": detail} 
            )
        
        if exc.status_code == 403:
            referer = request.headers.get("referer", "/")
            if "text/html" in request.headers.get("accept", ""):
                return RedirectResponse(
                    url=f"{referer}?error={detail}", 
                    status_code=303
                )
            return JSONResponse(
                status_code=403,
                content={"detail": detail}
            )

        # Для всех остальных статус-кодов
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail} 
        )
    
    return application

app = get_application()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)