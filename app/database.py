import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_async_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session