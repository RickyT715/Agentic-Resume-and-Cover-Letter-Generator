"""Async database session management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

logger = logging.getLogger(__name__)

# Engine and session factory (initialized lazily)
_engine = None
_session_factory = None


def get_engine():
    """Get or create the async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        if not settings.database_url:
            logger.warning("DATABASE_URL not configured - database features disabled")
            return None
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_size=5,
            max_overflow=10,
        )
        logger.info(
            f"Database engine created: {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'local'}"
        )
    return _engine


def get_session_factory():
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        if engine is None:
            return None
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session with automatic cleanup."""
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL in .env")
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db():
    """Initialize database connection and create tables if needed."""
    engine = get_engine()
    if engine is None:
        logger.info("Skipping database initialization (DATABASE_URL not set)")
        return

    from db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def close_db():
    """Close the database engine."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed")
