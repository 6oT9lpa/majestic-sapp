from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    
    REDIS_URL = "redis://redis:6379/0"
    REDIS_EXPIRE_SECONDS = 600
    
    EMAIL_TEMPLATES_DIR: str = "email-templates"
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 1440 
    EMAIL_FROM: str = "test_email@doc-generator.ru"
    SMTP_HOST: str = "smtp.beget.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "test_email@doc-generator.ru"
    SMTP_PASSWORD: str = "TestEmail123!"
    BASE_URL: str = "http://127.0.0.1:8000"
