from fastapi import APIRouter,Depends,HTTPException
from api.models import MonitorCreate,MonitorResponse,MonitorListResponse
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from api.db.models import Monitor as MonitorDB
from api.db.database import get_db

router =APIRouter(prefix="/monitors",tags=["Monitors"])


# GET endpoint — returns monitors from PostgreSQL.
# response_model tells FastAPI exactly what the API response should contain.
@router.get("/", response_model=MonitorListResponse)
async def get_monitors(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitorDB)
    )

    monitors = result.scalars().all()

    return {"monitors": monitors}

# POST endpoint — creates a new monitor in PostgreSQL.
@router.post("/", response_model=MonitorResponse)
async def create_monitor(
    monitor: MonitorCreate,
    db: AsyncSession = Depends(get_db),
):
    # Convert the validated API input into a database model.
    new_monitor = MonitorDB(
        name=monitor.name,
        url=str(monitor.url),
    )

    # Add it to the current database transaction.
    db.add(new_monitor)

    # Permanently save the new monitor.
    await db.commit()

    # Retrieve database-generated values such as the ID.
    await db.refresh(new_monitor)

    return new_monitor

@router.delete("/{monitor_id}",status_code=204)
#204 means no content there empty
async def delete_monitor(
    monitor_id:int,
    db:AsyncSession=Depends(get_db),
):
    result=await db.execute(
        select(MonitorDB).where(MonitorDB.id == monitor_id)
    )
    monitor=result.scalar_one_or_none()

    if monitoor is None:
        raise HTTTPExeption(
            status_code=404,
            detail="Monitor not found",
        )
    await db.delete(monitor)
    await db.commit()

from api.models import(
    MonitorCreate,
    MonitorResponse,
    MonitorListResponse,
    MonitorUpdate,
)

#put endpoint for the update an existing monitor
@router.put("/{monitor_id}",response_model=MonitorResponse)
async def update_monitor(
    monitor_id:int,
    monitor_data:MonitorUpdate,
    db:AsyncSession = Depends(get_db),
):
    #find the monitor which we want to updaate
    result=await db.execute(
        select(MonitorDB).where(MonitorDB.id== monitor_id)
    )
    monitor=result.scalar_one_or_none()
    #if 404 means monitor not exist

    if monitor is None:
        raise HTTPException(
            status_code=404,
            detail="Monitor not found",
        )
    #update the existing db reocrd
    monitor.name= monitor_data.name
    monitor.url=str(monitor_data.url);

    await db.commit()
    await db.refresh(monitor)
    return monitor

