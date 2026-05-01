from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import guacamole
from app.database import get_db
from app.models import User, Workspace
from app.schemas import NetworkAssign, WorkspaceCreate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("/")
async def create_workspace(payload: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    # Get user
    result = await db.execute(
        select(User).where(User.external_user_id == payload.external_user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # Prevent duplicate instance
    existing = await db.execute(
        select(Workspace).where(
            Workspace.external_instance_id == payload.external_instance_id
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "exists"}

    # Create Guacamole connection
    connection_id = await guacamole.create_connection(
        payload.fixed_ip,
        payload.workspace_name
    )

    # Grant permission
    await guacamole.grant_user_permission(user.username, connection_id)

    workspace = Workspace(
        external_instance_id=payload.external_instance_id,
        user_id=user.external_user_id,
        workspace_name=payload.workspace_name,
        fixed_ip=payload.fixed_ip,
        guacamole_connection_id=connection_id
    )

    db.add(workspace)
    await db.commit()

    return {"status": "created"}


@router.patch("/{external_instance_id}/network")
async def assign_network(external_instance_id: str, payload: NetworkAssign, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workspace).where(Workspace.external_instance_id == external_instance_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(404)

    # Update Guacamole
    await guacamole.update_connection(
        workspace.guacamole_connection_id,
        payload.floating_ip
    )

    workspace.floating_ip = payload.floating_ip
    await db.commit()

    return {"status": "updated"}

@router.delete("/{external_instance_id}")
async def delete_workspace(external_instance_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workspace).where(Workspace.external_instance_id == external_instance_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(404)

    await guacamole.delete_connection(workspace.guacamole_connection_id)

    await db.delete(workspace)
    await db.commit()

    return {"status": "deleted"}