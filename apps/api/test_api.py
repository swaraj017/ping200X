
import pytest
import pytest_asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.db.database import get_db
from api.db.models import Base
from api.main import app


# Create an isolated SQLite database and HTTP client for API integration tests.
# Override the production database dependency to prevent tests from accessing Neon.
# Clean up the dependency override and database engine after each test.
@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:"
    )

    test_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create the database tables in the temporary test database.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    # Replace the production database session with a test database session.
    async def override_get_db():
        async with test_session() as session:
            yield session

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db

    try:
        # Send HTTP requests directly to the FastAPI application.
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override

        await engine.dispose()


@pytest.mark.asyncio
async def test_create_monitor(client):
    # Create a monitor through the API endpoint.
    response = await client.post(
        "/monitors/",
        json={
            "name": "Example",
            "url": "https://example.com",
        },
    )

    # Verify the API successfully creates the monitor.
    assert response.status_code == 200

    # Verify the returned monitor data.
    data = response.json()
    assert data["name"] == "Example"
    assert data["url"] == "https://example.com/"
    assert isinstance(data["id"], int)


@pytest.mark.asyncio
async def test_list_monitors(client):
    # Create a monitor first.
    await client.post(
        "/monitors/",
        json={
            "name": "Example",
            "url": "https://example.com",
        },
    )

    # Fetch the monitor list.
    response = await client.get("/monitors/")

    assert response.status_code == 200
    data = response.json()
    assert len(data["monitors"]) == 1
    assert data["monitors"][0]["name"] == "Example"
    assert data["monitors"][0]["url"] == "https://example.com/"



@pytest.mark.asyncio
async def test_delete_monitor(client):
    # Create a monitor to delete.
    create_response = await client.post(
        "/monitors/",
        json={
            "name": "Delete Me",
            "url": "https://example.com",
        },
    )
    monitor_id = create_response.json()["id"]

    # Delete the monitor.
    response = await client.delete(f"/monitors/{monitor_id}")
    assert response.status_code in (200, 204)

    # Verify the monitor no longer exists in the list.
    list_response = await client.get("/monitors/")
    monitors = list_response.json()["monitors"]
    assert all(monitor["id"] != monitor_id for monitor in monitors)



@pytest.mark.asyncio
async def test_update_monitor(client):
    # Create a monitor to update.
    create_response = await client.post(
        "/monitors/",
        json={
            "name": "Example",
            "url": "https://example.com",
        },
    )
    monitor_id = create_response.json()["id"]

    # Update the monitor's name and URL.
    response = await client.put(
        f"/monitors/{monitor_id}",
        json={
            "name": "Updated Example",
            "url": "https://httpbin.org",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Example"
    assert data["url"] == "https://httpbin.org/"
    assert data["id"] == monitor_id



@pytest.mark.asyncio
async def test_get_missing_monitor_history(client):
    # Request history for a monitor that does not exist.
    response = await client.get("/monitors/999999/history")

    # The API should return 404 instead of crashing.
    assert response.status_code == 404
