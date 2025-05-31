from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from formation_ia_backend.core.config import settings

async_engine = create_async_engine(settings.DATABASE_URL, echo=True) # echo=True for dev, can be removed for prod

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit() # This commit might be too broad for some use cases, often commit is handled in services/use_cases
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
