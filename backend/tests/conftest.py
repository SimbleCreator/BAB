"""Test setup: a real PostgreSQL test database (BAB_TEST_DATABASE_URL), migrated with
Alembic once per run and truncated before every test."""

import asyncio
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import httpx
import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import get_settings
from app.core.database import get_session
from app.core.rate_limit import login_limiter, register_limiter
from app.main import create_app
from app.models import Base

TEST_DB_URL = get_settings().test_database_url
BACKEND_DIR = Path(__file__).resolve().parents[1]


async def _recreate_schema() -> None:
    eng = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async with eng.begin() as conn:
        # Drops every table, type and sequence the test user owns. Unlike dropping the
        # public schema, this works whoever owns the schema itself.
        await conn.execute(text("DROP OWNED BY CURRENT_USER CASCADE"))
    await eng.dispose()


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    asyncio.run(_recreate_schema())
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    command.upgrade(cfg, "head")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    eng = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with eng.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    login_limiter.reset()
    register_limiter.reset()
    yield async_sessionmaker(eng, expire_on_commit=False)
    await eng.dispose()


@pytest.fixture
async def session(sessionmaker) -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as s:
        yield s


@pytest.fixture
async def make_client(sessionmaker) -> AsyncIterator[Callable[[], httpx.AsyncClient]]:
    """Factory for independent clients (separate cookie jars), e.g. a second user."""
    clients: list[httpx.AsyncClient] = []

    def _make() -> httpx.AsyncClient:
        app = create_app()

        async def _session() -> AsyncIterator[AsyncSession]:
            async with sessionmaker() as s:
                yield s

        app.dependency_overrides[get_session] = _session
        # https so the Secure refresh cookie is stored and sent back.
        c = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://test",
            headers={"X-BAB-Client": "test"},
        )
        clients.append(c)
        return c

    yield _make
    for c in clients:
        await c.aclose()


@pytest.fixture
async def client(make_client) -> httpx.AsyncClient:
    return make_client()
