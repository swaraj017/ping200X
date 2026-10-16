
from fastapi import Query
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select,desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    MonitorCreate,
    MonitorResponse,
    MonitorListResponse,
    MonitorUpdate,
)
from api.db.models import Monitor as MonitorDB, MonitorCheck
from api.db.database import get_db
from api.services.health_checker import check_url


router = APIRouter(prefix="/monitors", tags=["Monitors"])


# GET: Return all saved monitors.
@router.get("/", response_model=MonitorListResponse)
async def get_monitors(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MonitorDB))
    monitors = result.scalars().all()

    return {"monitors": monitors}


# POST: Create a new monitor.
@router.post("/", response_model=MonitorResponse)
async def create_monitor(
    monitor: MonitorCreate,
    db: AsyncSession = Depends(get_db),
):
    new_monitor = MonitorDB(
        name=monitor.name,
        url=str(monitor.url),
    )

    db.add(new_monitor)
    await db.commit()
    await db.refresh(new_monitor)

    return new_monitor


# DELETE: Remove a monitor.
@router.delete("/{monitor_id}", status_code=204)
async def delete_monitor(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitorDB).where(MonitorDB.id == monitor_id)
    )
    monitor = result.scalar_one_or_none()

    if monitor is None:
        raise HTTPException(
            status_code=404,
            detail="Monitor not found",
        )

    await db.delete(monitor)
    await db.commit()


# PUT: Update an existing monitor.
@router.put("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: int,
    monitor_data: MonitorUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitorDB).where(MonitorDB.id == monitor_id)
    )
    monitor = result.scalar_one_or_none()

    if monitor is None:
        raise HTTPException(
            status_code=404,
            detail="Monitor not found",
        )

    monitor.name = monitor_data.name
    monitor.url = str(monitor_data.url)

    await db.commit()
    await db.refresh(monitor)

    return monitor


# POST: Check a monitor and save the result to history.
@router.post("/{monitor_id}/check")
async def run_monitor_check(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
):
    # Find the saved monitor.
    result = await db.execute(
        select(MonitorDB).where(MonitorDB.id == monitor_id)
    )
    monitor = result.scalar_one_or_none()

    if monitor is None:
        raise HTTPException(
            status_code=404,
            detail="Monitor not found",
        )

    # Check the website.
    check_result = await check_url(monitor.url)

    # Store this check in PostgreSQL.
    history = MonitorCheck(
        monitor_id=monitor.id,
        status=check_result["status"],
        status_code=check_result.get("status_code"),
        response_time_ms=check_result.get("response_time_ms"),
        error=check_result.get("error"),
    )

    db.add(history)
    await db.commit()
    await db.refresh(history)

    # Return the result and its saved history ID.
    return {
        "monitor_id": monitor.id,
        "name": monitor.name,
        "url": monitor.url,
        **check_result,
        "check_id": history.id,
        "checked_at": history.checked_at,
    }

# GET: Return recent check history for a monitor.
@router.get("/{monitor_id}/history")
async def get_monitor_history(
    monitor_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitorDB).where(MonitorDB.id == monitor_id)
    )
    monitor = result.scalar_one_or_none()

    if monitor is None:
        raise HTTPException(
            status_code=404,
            detail="Monitor not found",
        )

    result = await db.execute(
        select(MonitorCheck)
        .where(MonitorCheck.monitor_id == monitor_id)
        .order_by(desc(MonitorCheck.checked_at))
        .limit(limit)
    )
    history = result.scalars().all()

    return {
        "monitor_id": monitor.id,
        "name": monitor.name,
        "history": history,
    }


# GET: Calculate uptime from recorded checks.
@router.get("/{monitor_id}/uptime")
async def get_monitor_uptime(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitorDB).where(MonitorDB.id == monitor_id)
    )
    monitor = result.scalar_one_or_none()

    if monitor is None:
        raise HTTPException(
            status_code=404,
            detail="Monitor not found",
        )

    result = await db.execute(
        select(MonitorCheck).where(
            MonitorCheck.monitor_id == monitor_id
        )
    )
    checks = result.scalars().all()

    total_checks = len(checks)
    up_checks = sum(1 for check in checks if check.status == "UP")

    uptime_percentage = (
        round((up_checks / total_checks) * 100, 2)
        if total_checks > 0
        else None
    )

    return {
        "monitor_id": monitor.id,
        "name": monitor.name,
        "total_checks": total_checks,
        "up_checks": up_checks,
        "down_checks": total_checks - up_checks,
        "uptime_percentage": uptime_percentage,
    }

