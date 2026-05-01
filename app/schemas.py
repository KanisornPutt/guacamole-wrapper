from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# -------- USERS --------
class UserCreate(BaseModel):
    external_user_id: str
    username: str


class UserResponse(BaseModel):
    external_user_id: str
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


# -------- WORKSPACES --------
class WorkspaceCreate(BaseModel):
    external_instance_id: str
    external_user_id: str
    workspace_name: str
    fixed_ip: str


class WorkspaceResponse(BaseModel):
    external_instance_id: str
    workspace_name: str
    is_active: bool
    guacamole_connection_id: Optional[int]

    class Config:
        from_attributes = True

class NetworkAssign(BaseModel):
    floating_ip: str