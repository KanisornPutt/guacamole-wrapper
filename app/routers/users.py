from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import guacamole
from app.database import get_db
from app.models import User
from app.schemas import UserCreate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/")
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check existing
    result = await db.execute(
        select(User).where(User.external_user_id == payload.external_user_id)
    )
    if result.scalar_one_or_none():
        return {"status": "exists"}

    # Create in Guacamole
    await guacamole.create_user(payload.username)

    user = User(
        external_user_id=payload.external_user_id,
        username=payload.username
    )

    db.add(user)
    await db.commit()

    return {"status": "created"}


