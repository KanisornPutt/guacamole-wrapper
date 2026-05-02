from fastapi import APIRouter, Depends, HTTPException
import httpx
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import guacamole
from app.database import get_db
from app.models import User, Workspace
from app.schemas import NetworkAssign, WorkspaceCreate

logger = logging.getLogger(__name__)

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

    workspace = Workspace(
        external_instance_id=payload.external_instance_id,
        user_id=user.external_user_id,
        workspace_name=payload.workspace_name,
        os_username=payload.os_username,
        os_password=payload.os_password,
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

    response_data = {}

    if workspace.guacamole_connection_id is None:
        user_result = await db.execute(
            select(User).where(User.external_user_id == workspace.user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(404, "User not found")

        connection_id, connection_group_id = await guacamole.create_connection(
            payload.floating_ip,
            workspace.workspace_name,
            workspace.os_username,
            workspace.os_password,
            connection_group_name=user.username,
        )
        response_data["create_connection"] = {"identifier": connection_id, "connection_group_id": connection_group_id}
        
        # Persist both connection_id and connection_group_id immediately to avoid duplicate creates and lookups
        workspace.guacamole_connection_id = connection_id
        workspace.guacamole_group_id = connection_group_id
        await db.commit()

        # Ensure the Guacamole user exists before granting permissions. If the user
        # already exists, ignore the conflict error (409 or 400 with "already exists").
        try:
            await guacamole.create_user(user.username)
            response_data["create_user"] = {"status": "created"}
        except httpx.HTTPStatusError as exc:
            if exc.response is None:
                raise
            # Guacamole returns 409 or 400 with "already exists" message
            status = exc.response.status_code
            if status == 409:
                response_data["create_user"] = {"status": "already_exists"}
            elif status == 400:
                try:
                    body_text = exc.response.text or ""
                    if "already exists" not in body_text.lower():
                        raise
                    response_data["create_user"] = {"status": "already_exists"}
                except Exception:
                    raise
            else:
                raise

        # Grant permission to the connection group first (if it exists)
        if connection_group_id:
            try:
                group_perm_response = await guacamole.grant_user_connection_group_permission(user.username, connection_group_id)
                response_data["grant_user_connection_group_permission"] = group_perm_response
                logger.info(f"Granted connection group permission to user {user.username} for group {connection_group_id}")
            except Exception as e:
                logger.warning(f"Failed to grant connection group permission to user {user.username} for group {connection_group_id}: {e}")
                # Don't fail if group permission fails

        # Grant permission to the connection after we've persisted the connection id
        try:
            perm_response = await guacamole.grant_user_permission(user.username, connection_id)
            response_data["grant_user_permission"] = perm_response
            logger.info(f"Granted permission to user {user.username} for connection {connection_id}")
        except Exception as e:
            logger.error(f"Failed to grant permission to user {user.username} for connection {connection_id}: {e}")
            raise
    else:
        # Update Guacamole connection
        update_response = await guacamole.update_connection(
            workspace.guacamole_connection_id,
            payload.floating_ip
        )
        response_data["update_connection"] = update_response
        
        # Also re-grant permission on update to ensure it's set
        user_result = await db.execute(
            select(User).where(User.external_user_id == workspace.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            # Re-grant connection group permission if we have a stored group_id
            if workspace.guacamole_group_id:
                try:
                    group_perm_response = await guacamole.grant_user_connection_group_permission(user.username, workspace.guacamole_group_id)
                    response_data["grant_user_connection_group_permission"] = group_perm_response
                    logger.info(f"Re-granted connection group permission to user {user.username} for group {workspace.guacamole_group_id}")
                except Exception as e:
                    logger.warning(f"Failed to re-grant connection group permission to user {user.username} for group {workspace.guacamole_group_id}: {e}")
                    # Try to find and recreate the group if it doesn't exist
                    try:
                        recreated_group_id = await guacamole._ensure_connection_group(user.username)
                        if recreated_group_id:
                            workspace.guacamole_group_id = recreated_group_id
                            await db.commit()
                            retry_response = await guacamole.grant_user_connection_group_permission(user.username, recreated_group_id)
                            response_data["grant_user_connection_group_permission"] = retry_response
                            logger.info(f"Recreated and re-granted connection group permission for user {user.username}, new group_id: {recreated_group_id}")
                    except Exception as retry_error:
                        logger.warning(f"Failed to recreate group and retry: {retry_error}")
            
            # Re-grant connection permission
            try:
                perm_response = await guacamole.grant_user_permission(user.username, workspace.guacamole_connection_id)
                response_data["grant_user_permission"] = perm_response
                logger.info(f"Re-granted permission to user {user.username} for connection {workspace.guacamole_connection_id}")
            except Exception as e:
                logger.warning(f"Failed to re-grant permission to user {user.username}: {e}")
                # Don't fail the update if permission re-grant fails

    workspace.floating_ip = payload.floating_ip
    await db.commit()

    return {"status": "updated", **response_data}

@router.delete("/{external_instance_id}")
async def delete_workspace(external_instance_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workspace).where(Workspace.external_instance_id == external_instance_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(404)

    if workspace.guacamole_connection_id is not None:
        await guacamole.delete_connection(workspace.guacamole_connection_id)

    await db.delete(workspace)
    await db.commit()

    return {"status": "deleted"}