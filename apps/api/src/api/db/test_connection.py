import asyncio

from sqlalchemy import text
from api.db.database import engine

async def test_connection():
    async with engine.connect() as connection:
        result= await connection.execute(text("SELECT 1"))
        print("DB CONNECTED ",result.scalar()==1)


asyncio.run(test_connection())