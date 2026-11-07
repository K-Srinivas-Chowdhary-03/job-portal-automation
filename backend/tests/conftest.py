import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base, get_db
from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from uuid import uuid4

# Override database URL for tests – use SQLite in‑memory async engine
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_db.sqlite"

# Create async engine for tests
@pytest.fixture(scope="session")
def event_loop():
    # Reuse the same event loop for all async fixtures
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Drop tables after the session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(async_engine):
    """Provide a fresh async DB session for each test and rollback after."""
    async_session = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with async_session() as session:
        async with session.begin():
            yield session
        # Rollback any changes made during the test
        await session.rollback()

# Override FastAPI dependency to use the test session
@pytest.fixture(autouse=True)
def override_get_db(db_session):
    async def _override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

# Helper to create a user and return its JWT token
@pytest.fixture
async def admin_user(db_session):
    admin = User(
        id=uuid4(),
        name="Admin User",
        email="admin@example.com",
        password_hash="hashed",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(str(admin.id))
    return {"user": admin, "token": token}

@pytest.fixture
async def regular_user(db_session):
    user = User(
        id=uuid4(),
        name="Regular User",
        email="user@example.com",
        password_hash="hashed",
        role="USER",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(str(user.id))
    return {"user": user, "token": token}
