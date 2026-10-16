
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




from datetime import datetime, timezone

import pytest
from api.db.models import MonitorCheck


@pytest.mark.asyncio
async def test_monitor_history_respects_limit(client):
    create_response = await client.post(
        "/monitors/",
        json={
            "name": "History Test",
            "url": "https://example.com",
        },
    )
    assert create_response.status_code == 200
    monitor_id = create_response.json()["id"]

    # Insert three checks directly into the isolated test database.
    from api.db.database import get_db

    async for db in app.dependency_overrides[get_db]():
        timestamps = [
            datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc),
        ]

        db.add_all([
            MonitorCheck(
                monitor_id=monitor_id,
                status="UP",
                status_code=200,
                response_time_ms=100,
                checked_at=timestamp,
            )
            for timestamp in timestamps
        ])
        await db.commit()
        break

    response = await client.get(
        f"/monitors/{monitor_id}/history?limit=2"
    )

    assert response.status_code == 200
    history = response.json()["history"]
    assert len(history) == 2
    assert history[0]["checked_at"] >= history[1]["checked_at"]


@pytest.mark.asyncio
async def test_monitor_uptime_with_mixed_results(client):
    create_response = await client.post(
        "/monitors/",
        json={
            "name": "Uptime Test",
            "url": "https://example.com",
        },
    )
    assert create_response.status_code == 200
    monitor_id = create_response.json()["id"]

    from api.db.database import get_db

    async for db in app.dependency_overrides[get_db]():
        db.add_all([
            MonitorCheck(
                monitor_id=monitor_id,
                status="UP",
                status_code=200,
                response_time_ms=100,
            ),
            MonitorCheck(
                monitor_id=monitor_id,
                status="UP",
                status_code=200,
                response_time_ms=120,
            ),
            MonitorCheck(
                monitor_id=monitor_id,
                status="DOWN",
                status_code=None,
                response_time_ms=10000,
                error="Request timed out",
            ),
            MonitorCheck(
                monitor_id=monitor_id,
                status="UP",
                status_code=200,
                response_time_ms=90,
            ),
        ])
        await db.commit()
        break

    response = await client.get(
        f"/monitors/{monitor_id}/uptime"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_checks"] == 4
    assert data["up_checks"] == 3
    assert data["down_checks"] == 1
    assert data["uptime_percentage"] == 75.0


@pytest.mark.asyncio
async def test_monitor_uptime_without_checks(client):
    create_response = await client.post(
        "/monitors/",
        json={
            "name": "New Monitor",
            "url": "https://example.com",
        },
    )
    assert create_response.status_code == 200
    monitor_id = create_response.json()["id"]

    response = await client.get(
        f"/monitors/{monitor_id}/uptime"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_checks"] == 0
    assert data["up_checks"] == 0
    assert data["down_checks"] == 0
    assert data["uptime_percentage"] is None



@pytest.mark.asyncio
async def test_create_monitor_rejects_localhost(client):
    response = await client.post(
        "/monitors/",
        json={
            "name": "Unsafe Monitor",
            "url": "http://localhost",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_monitor_rejects_private_ip(client):
    create_response = await client.post(
        "/monitors/",
        json={
            "name": "Example",
            "url": "https://example.com",
        },
    )
    assert create_response.status_code == 200

    monitor_id = create_response.json()["id"]

    response = await client.put(
        f"/monitors/{monitor_id}",
        json={
            "name": "Example",
            "url": "http://192.168.1.1",
        },
    )

    assert response.status_code == 422

    # The original monitor must remain unchanged.
    list_response = await client.get("/monitors/")
    monitor = list_response.json()["monitors"][0]
    assert monitor["url"] == "https://example.com/"