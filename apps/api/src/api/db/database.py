from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession
from pydantic_settings import BaseSettings, SettingsConfigDict
from api.db.models import Base

from sqlalchemy.orm import sessionmaker

class Settings(BaseSettings):
    DB_URL: str
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

engine = create_async_engine(settings.DB_URL)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

