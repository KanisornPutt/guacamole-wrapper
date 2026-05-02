from sqlalchemy import String, Boolean, ForeignKey, TIMESTAMP, func, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class User(Base):
    __tablename__ = "users"

    external_user_id = mapped_column(String(36), primary_key=True)
    username = mapped_column(String(255), unique=True, nullable=False)

    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Workspace(Base):
    __tablename__ = "workspaces"

    external_instance_id = mapped_column(String(36), primary_key=True)

    user_id = mapped_column(ForeignKey("users.external_user_id", ondelete="CASCADE"))

    guacamole_connection_id = mapped_column(Integer, unique=True)
    guacamole_group_id = mapped_column(Integer, nullable=True)

    workspace_name = mapped_column(String(255))
    os_username = mapped_column(String(255), nullable=True)
    os_password = mapped_column(String(255), nullable=True)
    floating_ip = mapped_column(String(45), nullable=True)

    is_active = mapped_column(Boolean, default=True)

    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())