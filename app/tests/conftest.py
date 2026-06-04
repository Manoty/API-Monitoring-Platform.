import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base, get_db
from app.main import app

# use a separate test DB
TEST_DATABASE_URL = "postgresql+asyncpg://monitor:monitor@localhost:5432/apimonitor_test"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,   # no pooling in tests — each test gets clean state
)

TestSessionFactory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all tables once per test session, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """Truncate all tables between tests — keeps tests isolated."""
    yield
    async with TestSessionFactory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """Yield a test DB session."""
    async with TestSessionFactory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncClient:
    """
    Yield an async test client with the DB dependency overridden
    so all routes use the test database.
    """
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()