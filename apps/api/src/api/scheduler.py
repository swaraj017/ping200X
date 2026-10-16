
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from api.db.database import AsyncSessionLocal
from api.db.models import Monitor as MonitorDB
from api.db.models import MonitorCheck
from api.services.health_checker import check_url


async def check_all_monitors():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MonitorDB))
        monitors = result.scalars().all()

        for monitor in monitors:
            try:
                check_result = await check_url(monitor.url)

                history = MonitorCheck(
                    monitor_id=monitor.id,
                    status=check_result["status"],
                    status_code=check_result.get("status_code"),
                    response_time_ms=check_result["response_time_ms"],
                    error=check_result.get("error"),
                )

                db.add(history)

            except Exception as error:
                print(f"Scheduled check failed for monitor {monitor.id}: {error}")

        await db.commit()


scheduler = AsyncIOScheduler()


def start_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        check_all_monitors,
        trigger="interval",
        seconds=60,
        id="monitor_checks",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    print("Ping200X scheduler started: checks every 60 seconds")