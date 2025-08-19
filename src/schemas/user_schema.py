from pydantic import BaseModel, EmailStr, Field, validator, model_validator
from typing import Optional
import re

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    password_confirm: str

    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_ .]+$', v): 
            raise ValueError('Никнейм должен содержать только буквы, цифры, пробелы, точки и подчеркивания')
        return v

    @validator('password_confirm')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Пароли не совпадают')
        return v

    @validator('password')
    def validate_password(cls, v):
        errors = []
        if len(v) < 8:
            errors.append("Минимум 8 символов")
        if not re.search(r'[A-Z]', v):
            errors.append("Хотя бы одна заглавная буква")
        if not re.search(r'[a-z]', v):
            errors.append("Хотя бы одна строчная буква")
        if not re.search(r'[0-9]', v):
            errors.append("Хотя бы одна цифра")
        
        if errors:
            raise ValueError("Пароль не соответствует требованиям: " + ", ".join(errors))
        return v

class UserLogin(BaseModel):
    login: str  
    password: str

    @validator('login')
    def validate_login(cls, v):
        if '@' in v:
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', v):
                raise ValueError('Введите корректный email')
        else:
            if len(v) < 3 or len(v) > 50: 
                raise ValueError('Никнейм должен быть от 3 до 40 символов')
            if not re.match(r'^[a-zA-Z0-9_ .]+$', v):
                raise ValueError('Никнейм должен содержать только буквы, цифры, пробелы, точки и подчеркивания')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        return v

class ChangePaswRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def check_passwords_different(self):
        if self.current_password == self.new_password:
            raise ValueError("Пароли не должны совпадать")
        return self

    @staticmethod
    def validate_password_strength(password: str):
        errors = []
        if len(password) < 8:
            errors.append("Минимум 8 символов")
        if not re.search(r'[A-Z]', password):
            errors.append("Хотя бы одна заглавная буква")
        if not re.search(r'[a-z]', password):
            errors.append("Хотя бы одна строчная буква")
        if not re.search(r'[0-9]', password):
            errors.append("Хотя бы одна цифра")
        return errors

    @model_validator(mode="before")
    def validate_new_password(cls, data):
        new_password = data.get("new_password")
        if new_password:
            errors = cls.validate_password_strength(new_password)
            if errors:
                raise ValueError("Пароль не соответствует требованиям: " + ", ".join(errors))
        return data

class ChangeUsernameRequest(BaseModel):
    new_username: str = Field(min_length=3, max_length=50)
    
    @validator('new_username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_ .]+$', v):
            raise ValueError('Никнейм должен содержать только буквы, цифры, пробелы, точки и подчеркивания')
        return v

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None