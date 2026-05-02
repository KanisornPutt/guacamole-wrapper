from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    external_user_id: str
    username: str


class WorkspaceCreate(BaseModel):
    external_instance_id: str
    external_user_id: str
    username: Optional[str] = None
    workspace_name: str
    os_username: Optional[str] = None
    os_password: Optional[str] = None


class NetworkAssign(BaseModel):
    floating_ip: str


class NetworkDisassociate(BaseModel):
    floating_ip: str