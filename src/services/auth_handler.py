from datetime import datetime, timedelta
from typing import Optional, Union
from sqlalchemy import select, or_, and_, func
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
from fastapi import HTTPException, status, Response, Request
import uuid
import jwt

from src.config import Config
from src.schemas.user_schema import Token
from src.models.user_model import User, UserBan
from src.models.role_model import Role

from src.database import get_session

security = HTTPBearer()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        
        if payload.get("type") not in ["access", "refresh", "email_verification", None]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return payload
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

def set_auth_cookies(response: Response, tokens: Token) -> None:
    """Устанавливает HttpOnly cookies с токенами"""
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        secure=False, 
        samesite="lax",
        max_age=Config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=Config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/"
    )

def clear_auth_cookies(response: Response) -> None:
    """Очищает cookies аутентификации"""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")

async def get_current_user(request: Request, raise_exception: bool = True) -> dict:
    """Получает пользователя из access token cookie"""
    token = request.cookies.get("access_token")
    if not token:
        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        return None
    
    try:
        payload = decode_token(token)
        
        if payload.get("type") == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cannot be used as access token"
            )
        
        user_id = uuid.UUID(payload.get("sub"))
        
        async for session in get_session():
            # Проверяем, не заблокирован ли пользователь
            ban_result = await session.execute(
                select(UserBan)
                .where(
                    and_(
                        UserBan.user_id == user_id,
                        UserBan.is_active == True,
                        or_(
                            UserBan.expires_at == None,
                            UserBan.expires_at > func.now()
                        )
                    )
                )
            )
            ban = ban_result.scalar()
            
            if ban:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Ваш аккаунт заблокирован. Причина: {ban.reason}"
                )
            
            # Получаем пользователя и роль
            result = await session.execute(
                select(User, Role)
                .join(Role, User.role_id == Role.id)
                .where(User.id == user_id)
            )
            user, role = result.first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
                
            user.last_login = datetime.now()
            session.commit()
            
            return {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": {
                    "id": role.id,
                    "level": role.level,
                    "permissions": role.permissions,
                    "name": role.name
                },
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at
            }
    except HTTPException as e:
        if e.status_code == 403:
            raise
        if raise_exception:
            raise
        return None
    except Exception as e:
        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal authentication error: {str(e)}"
            )
        return None

async def get_current_user_websoket(token: str) -> dict:
    """Получает пользователя из access token"""
    try:
        payload = decode_token(token)
        
        if payload.get("type") == "refresh":
            raise Exception("Refresh token cannot be used as access token")
        
        user_id = uuid.UUID(payload.get("sub"))
        
        async for session in get_session():
            result = await session.execute(
                select(User, Role)
                .join(Role, User.role_id == Role.id)
                .where(User.id == user_id)
            )
            user, role = result.first()
            
            if not user:
                raise Exception("User not found")
            
            return {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": {
                    "id": role.id,
                    "level": role.level,
                    "permissions": role.permissions,
                    "name": role.name
                },
                "is_active": user.is_active,
                "last_login": user.last_login,
                "created_at": user.created_at
            }
            
    except jwt.ExpiredSignatureError:
        raise Exception("Срок действия токена истек")
    except jwt.PyJWTError:
        raise Exception("Недействительный токен")
    except Exception as e:
        raise Exception(f"Ошибка авторизации: {str(e)}")

async def get_username_by_id(user_id: uuid.UUID) -> dict:
    async for session in get_session():
        result = await session.execute(
            select(User)
            .where(User.id == user_id)
        )
        user = result.scalar()
        if not user:
            return None
        return user.username

def create_tokens(user: Union[User, str]) -> Token:
    """Создает токены, принимая либо объект User, либо user_id в виде строки"""
    access_token_expires = timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)
    
    user_id = str(user.id) if isinstance(user, User) else str(user)
    
    access_payload = {'sub': user_id}
    
    if isinstance(user, User) and user.role:
        access_payload.update({
            'role': {
                'level': user.role.level,
                'permissions': user.role.permissions
            }
        })
    
    access_token = create_access_token(
        data=access_payload, 
        expires_delta=access_token_expires
    )
    
    refresh_token = create_access_token(
        data={"sub": user_id, "type": "refresh"}, 
        expires_delta=refresh_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token
    )

def refresh_tokens(refresh_token: str) -> Token:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid type token"
        )
        
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return create_tokens(user_id)

def generate_email_verification_token(email: str) -> str:
    expires = datetime.utcnow() + timedelta(minutes=Config.EMAIL_VERIFICATION_EXPIRE_MINUTES)
    payload = {
        "email": email,
        "exp": expires,
        "type": "email_verification"
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.ALGORITHM)