import sys
import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Add backend root to path so tests can import services, models, etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest_asyncio.fixture(scope="session", autouse=True)
async def clean_test_users():
    """Remove test users created by auth tests so they can re-register cleanly."""
    from database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM users WHERE email IN ('test@scalper.io')"))
        await db.commit()


@pytest_asyncio.fixture(scope="session")
async def client():
    """Async test client against the live FastAPI app (session-scoped to share event loop)."""
    from main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
