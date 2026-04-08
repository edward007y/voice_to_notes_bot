from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.db.models import Base

# Створюємо асинхронний рушій
engine = create_async_engine(settings.db_url, echo=False)

# Фабрика сесій для виконання запитів
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ДОДАНО -> None
async def init_models() -> None:
    """Створює таблиці в БД (якщо вони ще не існують)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
