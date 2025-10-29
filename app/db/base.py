from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> None:
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(database_url, echo=False, future=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


@asynccontextmanager
async def session_factory() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database engine is not initialized")
    async with _session_factory() as session:
        yield session


def get_metadata():
    return Base.metadata
