from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config import Config
from src.models.base_model import Base 


engine = create_async_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    echo=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600
)

async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False
)

async def init_db():
    """Создает все таблицы в базе данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()