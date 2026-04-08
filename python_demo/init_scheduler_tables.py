import asyncio

from config.db_config import async_engine
from models.user import Base
from models.scheduler import CourseScheduleEvent, OfficialCalendarEvent, PersonalTodo


async def init_scheduler_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn,
                tables=[
                    PersonalTodo.__table__,
                    OfficialCalendarEvent.__table__,
                    CourseScheduleEvent.__table__,
                ]
            )
        )


if __name__ == "__main__":
    asyncio.run(init_scheduler_tables())
    print("scheduler tables initialized")
