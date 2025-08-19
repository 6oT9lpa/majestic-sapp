from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import BackgroundTasks
import jwt
import uuid
import json

from src.database import get_session
from src.schemas.user_schema import UserCreate, UserLogin, ChangePaswRequest, ChangeUsernameRequest
from src.models.user_model import User, UserRequest, UserRequestType
from src.config import Config
from src.services.auth_handler import (
    verify_password,
    get_password_hash,
    create_tokens,
    refresh_tokens,
    generate_email_verification_token,
    decode_token
)
from src.redis_client import redis_client
from src.models.role_model import Role
from src.services.email_service import send_verification_email_in_background

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def register_user(self, user_data: UserCreate, background_tasks: BackgroundTasks) -> dict:
        existing_user = await self.session.execute(
            select(User).where(
                (User.username == user_data.username) |
                (User.email == user_data.email)
            )
        )
        if existing_user.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ник или почта уже существует",
            )
        
        role = await self.session.execute(
            select(Role).where(Role.default_role == True)
        )
        default_role = role.scalars().first()
        
        if not default_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Возникла проблема, повторите попытку позже",
            )
        
        hashed_password = get_password_hash(user_data.password)
        
        user = User(
            username=user_data.username,
            email=user_data.email,
            hash_pasw=hashed_password,
            role_id=default_role.id,
            is_active=False 
        )
        
        verification_token = generate_email_verification_token(user.email)
        
        user_data_dict = {
            "username": user.username,
            "email": user.email,
            "hash_pasw": user.hash_pasw,
            "role_id": str(user.role_id),
            "verification_token": verification_token
        }
        await redis_client.setex(
            f"pending_user:{verification_token}", 
            Config.EMAIL_VERIFICATION_EXPIRE_MINUTES * 60,
            json.dumps(user_data_dict)
        )
        
        background_tasks.add_task(
            send_verification_email_in_background,
            background_tasks,
            user.email,
            verification_token
        )
        
        return {"message": "На вашу почту отправлено письмо с подтверждением"}

    async def verify_email(self, token: str) -> dict:
        # Сначала проверяем наличие записи в Redis
        user_data = await redis_client.get(f"pending_user:{token}")
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Токен недействителен или срок его действия истек"
            )
        
        try:
            user_data = json.loads(user_data)
            payload = decode_token(token)
            
            if payload.get("type") != "email_verification":
                await redis_client.delete(f"pending_user:{token}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Неверный тип токена"
                )
                
            if payload.get("email") != user_data["email"]:
                await redis_client.delete(f"pending_user:{token}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Несоответствие email в токене"
                )
                
            # Проверяем, что пользователь с таким email еще не существует
            existing_user = await self.session.execute(
                select(User).where(User.email == user_data["email"])
            )
            if existing_user.scalars().first():
                await redis_client.delete(f"pending_user:{token}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким email уже существует"
                )
                
            # Создаем пользователя
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hash_pasw=user_data["hash_pasw"],
                role_id=uuid.UUID(user_data["role_id"]),
                is_active=True
            )
            
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            
            await redis_client.delete(f"pending_user:{token}")
            
            tokens = create_tokens(user)
            
            return {
                "user": user,
                "tokens": tokens
            }
            
        except jwt.ExpiredSignatureError:
            await redis_client.delete(f"pending_user:{token}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Срок действия токена истек"
            )
        except (jwt.PyJWTError, json.JSONDecodeError, ValueError) as e:
            await redis_client.delete(f"pending_user:{token}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неверный токен: {str(e)}"
            )

    async def authenticate_user(self, credentials: UserLogin) -> dict:
        user = await self.session.scalar(
            select(User).where(
                (User.username == credentials.login) | 
                (User.email == credentials.login)
            )
        )
        
        if not user or not verify_password(credentials.password, user.hash_pasw):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Логин или пароль неверны',
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Аккаунт не активирован. Пожалуйста, подтвердите вашу почту.',
            )
        
        tokens = create_tokens(user)
        return {
            "user": user,
            "tokens": tokens,
        }
    
    async def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            tokens = refresh_tokens(refresh_token)
            return tokens
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )

    async def change_password(self, change_request: ChangePaswRequest, user_id: uuid.UUID) -> dict:
        """Изменение пароля пользователю"""
        try:
            current_user = await self.session.get(User, user_id)
            if not current_user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            
            if not verify_password(change_request.current_password, current_user.hash_pasw):
                raise HTTPException(status_code=400, detail="Неверный текущий пароль")
            
            hashed_password = get_password_hash(change_request.new_password)
            current_user.hash_pasw = hashed_password
            self.session.add(current_user)
            self.session.commit()
            
            return {"message": "Успешно"}
            
        except HTTPException:
            raise
        
        except Exception as e:
            print (f"Ошибка {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Произошла ошибка попробуйте позже"
            )
    
    async def change_username(self, change_data: ChangeUsernameRequest, user_id: uuid.UUID) -> dict:
        try: 
            current_user = await self.session.get(User, user_id)
            
            if not current_user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            
            existing_user = await self.session.execute(
                select(User).where(
                    (User.username == change_data.new_username)
                )
            )
            if existing_user.unique().scalars().first():
                raise HTTPException(
                    status_code=400,
                    detail="Ник уже существует",
                )
            
            if current_user.username == change_data.new_username:
                raise HTTPException(status_code=400, detail="Новый ник не должен совпадать с текущим")
            
            request_data = {
                "old_username": current_user.username,
                "new_username": change_data.new_username
            }
            
            new_request = UserRequest(
                user_id = current_user.id,
                request_type = UserRequestType.USERNAME_CHANGE,
                request_data = request_data
            )
            self.session.add(new_request)
            await self.session.commit()
            
            return {"message": "Успешно"}
            
        except HTTPException:
            raise
        
        except Exception as e:
            print (f"Ошибка: {str(e)}")
            raise HTTPException(status_code=500, detail="Произошла ошибка повторите позже")
    
    async def account_deletion_request(self, user_id: uuid.UUID) -> dict:
        try:
            current_user = await self.session.get(User, user_id)
            
            if not current_user: 
                raise HTTPException(status_code=404, detail="пользователь не найден")
            
            request_data = {
                "reason": "Пользователь хочет удалить аккаунт"
            }
            
            new_request = UserRequest(
                user_id = current_user.id,
                request_type = UserRequestType.ACCOUNT_DELETION,
                request_data = request_data
            )
            self.session.add(new_request)
            await self.session.commit()
            
            return {"message": "Успешно"}
        
        except HTTPException:
            raise
        
        except Exception as e:
            print (f"Ошибка {str(e)}")
            raise HTTPException(status_code=500, detail="Произошла ошибка попробуйте позже")
    
async def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session)

async def send_verification_email(email: str, token: str):
    verify_url = f"{Config.BASE_URL}/auth/verify-email?token={token}"
    print(f"Sending verification email to {email}")
    print(f"Verification URL: {verify_url}")
