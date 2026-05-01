import os
from typing import Dict

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("GUACAMOLE_BASE_URL", "")
DATA_SOURCE = os.getenv("GUACAMOLE_DATA_SOURCE", "")
GUACAMOLE_USERNAME = os.getenv("GUACAMOLE_USERNAME", "")
GUACAMOLE_PASSWORD = os.getenv("GUACAMOLE_PASSWORD", "")
GUACAMOLE_SSH_USERNAME = os.getenv("GUACAMOLE_SSH_USERNAME", "")
GUACAMOLE_SSH_PORT = os.getenv("GUACAMOLE_SSH_PORT", "22")
GUACAMOLE_NEW_USER_PASSWORD = os.getenv("GUACAMOLE_NEW_USER_PASSWORD", "")
GUACAMOLE_HTTP_TIMEOUT = float(os.getenv("GUACAMOLE_HTTP_TIMEOUT", "10"))

if not BASE_URL or not DATA_SOURCE:
    raise RuntimeError("GUACAMOLE_BASE_URL and GUACAMOLE_DATA_SOURCE must be set")


async def _get_token() -> str:
    if not GUACAMOLE_USERNAME or not GUACAMOLE_PASSWORD:
        raise RuntimeError("Guacamole credentials are not set")
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        response = await client.post(
            f"{BASE_URL}/tokens",
            data={"username": GUACAMOLE_USERNAME, "password": GUACAMOLE_PASSWORD},
        )
        response.raise_for_status()
        return response.json()["authToken"]


async def _auth_headers() -> Dict[str, str]:
    token = await _get_token()
    return {"Guacamole-Token": token}


def _connections_url() -> str:
    return f"{BASE_URL}/session/data/{DATA_SOURCE}/connections"


def _users_url() -> str:
    return f"{BASE_URL}/session/data/{DATA_SOURCE}/users"


async def create_user(username: str, password: str | None = None) -> None:
    user_password = password or GUACAMOLE_NEW_USER_PASSWORD
    if not user_password:
        raise RuntimeError("GUACAMOLE_NEW_USER_PASSWORD is not set")
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        response = await client.post(
            _users_url(),
            headers=await _auth_headers(),
            json={"username": username, "password": user_password, "attributes": {}},
        )
        response.raise_for_status()


async def create_connection(hostname: str, name: str) -> int:
    if not GUACAMOLE_SSH_USERNAME:
        raise RuntimeError("GUACAMOLE_SSH_USERNAME is not set")
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        response = await client.post(
            _connections_url(),
            headers=await _auth_headers(),
            json={
                "name": name,
                "protocol": "ssh",
                "parameters": {
                    "hostname": hostname,
                    "port": GUACAMOLE_SSH_PORT,
                    "username": GUACAMOLE_SSH_USERNAME,
                },
            },
        )
        response.raise_for_status()
        return int(response.json()["identifier"])


async def grant_user_permission(username: str, connection_id: int) -> None:
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        response = await client.patch(
            f"{_users_url()}/{username}/permissions",
            headers=await _auth_headers(),
            json=[
                {
                    "op": "add",
                    "path": f"/connectionPermissions/{connection_id}",
                }
            ],
        )
        response.raise_for_status()


async def update_connection(connection_id: int, hostname: str) -> None:
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        response = await client.patch(
            f"{_connections_url()}/{connection_id}",
            headers=await _auth_headers(),
            json={"parameters": {"hostname": hostname}},
        )
        response.raise_for_status()


async def delete_connection(connection_id: int) -> None:
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        response = await client.delete(
            f"{_connections_url()}/{connection_id}",
            headers=await _auth_headers(),
        )
        response.raise_for_status()