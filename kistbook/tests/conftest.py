from __future__ import annotations

import os

import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kistbook.api.main import app
from kistbook.db.models import Base
from kistbook.db.session import get_db

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/kistbook_test",
)

_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
_TestSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _test_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_schema():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with _TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def mock_wetarseel():
    with respx.mock(base_url="https://api.wetarseel.com") as mock:
        mock.post("/v1/messages").respond(
            200, json={"messages": [{"id": "wamid.test123"}]}
        )
        yield mock
