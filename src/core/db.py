# SQLAlchemy async engine + session
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.core.config import settings

# Створення асинхронного рушія бази даних
engine = create_async_engine(
    settings.db_url,
    echo=False,  # Змінити на True для логування SQL-запитів у консоль при дебагу
)

# Фабрика асинхронних сесій
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Базовий клас для всіх ORM-моделей
Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для отримання асинхронної сесії БД."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
