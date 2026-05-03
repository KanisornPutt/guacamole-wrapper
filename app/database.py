import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    dialect = os.getenv("DB_DIALECT", "postgresql+asyncpg")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    missing = [
        key
        for key, value in {
            "DB_NAME": name,
            "DB_USER": user,
            "DB_PASSWORD": password,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Database configuration is missing. Set DATABASE_URL or provide: "
            + ", ".join(missing)
        )

    return f"{dialect}://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = get_database_url()
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"

engine = create_async_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session