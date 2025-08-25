from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 43200))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    
    REDIS_URL = "redis://redis:6379/0"
    REDIS_EXPIRE_SECONDS = 600
    
    EMAIL_TEMPLATES_DIR: str = "email-templates"
    EMAIL_VERIFICATION_EXPIRE_MINUTES = int(os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", 1440))
    EMAIL_FROM = os.getenv("EMAIL_FROM", "test_email@doc-generator.ru")
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.beget.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    SMTP_USER = os.getenv("SMTP_USER", "test_email@doc-generator.ru")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "TestEmail123!")
    BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
