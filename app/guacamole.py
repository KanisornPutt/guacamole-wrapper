import os
from typing import Dict
import logging

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = os.getenv("GUACAMOLE_BASE_URL", "")
DATA_SOURCE = os.getenv("GUACAMOLE_DATA_SOURCE", "")
GUACAMOLE_USERNAME = os.getenv("GUACAMOLE_USERNAME", "")
GUACAMOLE_PASSWORD = os.getenv("GUACAMOLE_PASSWORD", "")
GUACAMOLE_SSH_USERNAME = os.getenv("GUACAMOLE_SSH_USERNAME", "")
GUACAMOLE_SSH_PASSWORD = os.getenv("GUACAMOLE_SSH_PASSWORD", "")
GUACAMOLE_SSH_PORT = int(os.getenv("GUACAMOLE_SSH_PORT", "22"))
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


def _connection_groups_url() -> str:
    return f"{BASE_URL}/session/data/{DATA_SOURCE}/connectionGroups"


def _users_url() -> str:
    return f"{BASE_URL}/session/data/{DATA_SOURCE}/users"


async def _find_connection_group_id_by_name(target_name: str) -> int | None:
    """Find a connection group by name in the /connectionGroups endpoint."""
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        r = await client.get(_connection_groups_url(), headers=await _auth_headers())
        r.raise_for_status()
        try:
            groups = r.json()
        except Exception:
            return None
        # Response can be a dict (id -> name or id -> obj) or a list of objects.
        if isinstance(groups, dict):
            for k, v in groups.items():
                if isinstance(v, str):
                    if v == target_name:
                        try:
                            return int(k)
                        except Exception:
                            return None
                elif isinstance(v, dict):
                    if v.get("name") == target_name:
                        ident = v.get("identifier") or k
                        try:
                            return int(ident)
                        except Exception:
                            return None
            return None
        if isinstance(groups, list):
            for g in groups:
                if isinstance(g, dict) and g.get("name") == target_name:
                    try:
                        return int(g.get("identifier"))
                    except Exception:
                        return None
        return None


async def _create_connection_group(group_name: str) -> int | None:
    """Create a connection group in Guacamole."""
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        payload = {"name": group_name, "type": "ORGANIZATIONAL", "attributes": {}, "parentIdentifier": "ROOT"}
        r = await client.post(_connection_groups_url(), headers=await _auth_headers(), json=payload)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            return None
        try:
            return int(r.json().get("identifier"))
        except Exception:
            return None


async def _ensure_connection_group(group_name: str) -> int | None:
    """Find or create a connection group."""
    if not group_name:
        return None
    existing = await _find_connection_group_id_by_name(group_name)
    if existing:
        logger.debug(f"Connection group '{group_name}' already exists with id {existing}")
        return existing
    logger.info(f"Creating new connection group '{group_name}'")
    return await _create_connection_group(group_name)






async def create_user(username: str, password: str | None = None) -> None:
    user_password = password or GUACAMOLE_NEW_USER_PASSWORD
    if not user_password:
        raise RuntimeError("GUACAMOLE_NEW_USER_PASSWORD is not set")
    
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        # 1. Create the user
        response = await client.post(
            _users_url(),
            headers=await _auth_headers(),
            json={"username": username, "password": user_password, "attributes": {}},
        )
        response.raise_for_status()

        # 2. Grant permission for the user to update their own account (change password)
        response = await client.patch(
            f"{_users_url()}/{username}/permissions",
            headers=await _auth_headers(),
            json=[
                {
                    "op": "add",
                    "path": f"/userPermissions/{username}",
                    "value": "UPDATE",  # allows changing own password
                }
            ],
        )
        response.raise_for_status()

        # 3. Grant system-level permission to update connections they have access to
        response = await client.patch(
            f"{_users_url()}/{username}/permissions",
            headers=await _auth_headers(),
            json=[
                {
                    "op": "add",
                    "path": "/systemPermissions",
                    "value": "CREATE_CONNECTION",  # allows editing connection parameters
                }
            ],
        )
        response.raise_for_status()


async def create_connection(
    hostname: str,
    name: str,
    username: str | None = None,
    password: str | None = None,
    connection_group_name: str | None = None,
) -> tuple[int, int | None]:
    connection_username = username or GUACAMOLE_SSH_USERNAME
    connection_password = password or GUACAMOLE_SSH_PASSWORD

    if not hostname:
        raise RuntimeError("hostname is not set")
    if not connection_username:
        raise RuntimeError("GUACAMOLE_SSH_USERNAME is not set")

    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        async def _find_connection_id_by_name(target_name: str) -> int | None:
            r = await client.get(_connections_url(), headers=await _auth_headers())
            r.raise_for_status()
            try:
                conns = r.json()
            except Exception:
                return None
            for conn in conns:
                if conn.get("name") == target_name:
                    return int(conn.get("identifier"))
            return None

        # determine parent group if requested and create the connection
        try:
            parent_identifier = None
            if connection_group_name:
                parent_identifier = await _ensure_connection_group(connection_group_name)

            body = {
                "name": name,
                "protocol": "ssh",
                "attributes": {},
                "parameters": {
                    "hostname": hostname,
                    "port": GUACAMOLE_SSH_PORT,
                    "username": connection_username,
                    **({"password": connection_password} if connection_password else {}),
                },
            }
            if parent_identifier:
                body["parentIdentifier"] = parent_identifier

            response = await client.post(_connections_url(), headers=await _auth_headers(), json=body)
            response.raise_for_status()
            connection_id = int(response.json()["identifier"])
            return (connection_id, parent_identifier)
        except httpx.HTTPStatusError as exc:
            resp = exc.response
            body_text = ""
            try:
                body_text = resp.text or ""
            except Exception:
                body_text = ""

            if resp is not None and (resp.status_code == 409 or "already exists" in body_text.lower()):
                existing = await _find_connection_id_by_name(name)
                if existing:
                    # Return existing connection with group if it was requested
                    group_id = None
                    if connection_group_name:
                        group_id = await _find_connection_group_id_by_name(connection_group_name)
                    return (existing, group_id)
            raise


async def grant_user_permission(username: str, connection_id: int) -> dict:
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        logger.info(
            f"Granting READ and UPDATE permissions for user={username}, connection={connection_id}"
        )
        response = await client.patch(
            f"{_users_url()}/{username}/permissions",
            headers=await _auth_headers(),
            json=[
                {
                    "op": "add",
                    "path": f"/connectionPermissions/{connection_id}",
                    "value": "READ",
                },
                {
                    "op": "add",
                    "path": f"/connectionPermissions/{connection_id}",
                    "value": "UPDATE",
                }
            ],
        )
        response.raise_for_status()
        logger.info(
            f"Permissions granted for user={username}, connection={connection_id}"
        )
        return {
            "status": "success",
            "response": response.json() if response.text else {},
        }


async def grant_user_connection_group_permission(username: str, group_id: int) -> dict:
    """Grant a user READ and UPDATE permission on a connection group."""
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        logger.info(
            f"Granting READ and UPDATE permissions for user={username}, connection_group={group_id}"
        )
        response = await client.patch(
            f"{_users_url()}/{username}/permissions",
            headers=await _auth_headers(),
            json=[
                {
                    "op": "add",
                    "path": f"/connectionGroupPermissions/{group_id}",
                    "value": "READ",
                },
                {
                    "op": "add",
                    "path": f"/connectionGroupPermissions/{group_id}",
                    "value": "UPDATE",
                }
            ],
        )
        response.raise_for_status()
        logger.info(
            f"Connection group permissions granted for user={username}, group={group_id}"
        )
        return {
            "status": "success",
            "response": response.json() if response.text else {},
        }



async def update_connection(connection_id: int, hostname: str) -> dict:
    async with httpx.AsyncClient(
        timeout=GUACAMOLE_HTTP_TIMEOUT,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        try:
            response = await client.patch(
                f"{_connections_url()}/{connection_id}",
                headers=await _auth_headers(),
                json={"parameters": {"hostname": hostname}},
            )
            response.raise_for_status()
            return {"method": "PATCH", "status": "success", "response": response.json() if response.text else {}}
        except httpx.HTTPStatusError as exc:
            resp = exc.response
            if resp is not None and resp.status_code == 405:
                # Some Guacamole installations do not accept PATCH for connections.
                # Retrieve the full connection object, update the hostname, and PUT it.
                try:
                    get_resp = await client.get(
                        f"{_connections_url()}/{connection_id}", headers=await _auth_headers()
                    )
                    get_resp.raise_for_status()
                    conn_obj = get_resp.json()
                    # Ensure parameters exists
                    if not isinstance(conn_obj, dict):
                        raise RuntimeError("Unexpected connection object format")
                    params = conn_obj.get("parameters") or {}
                    params["hostname"] = hostname
                    conn_obj["parameters"] = params
                    # Ensure attributes is present to avoid server NPEs
                    if "attributes" not in conn_obj or conn_obj["attributes"] is None:
                        conn_obj["attributes"] = {}
                    put_resp = await client.put(
                        f"{_connections_url()}/{connection_id}",
                        headers=await _auth_headers(),
                        json=conn_obj,
                    )
                    put_resp.raise_for_status()
                    return {"method": "PUT (via GET)", "status": "success", "response": put_resp.json() if put_resp.text else {}}
                except Exception:
                    # Fallback: try a safer PUT with attributes and parameters to avoid NPE
                    response = await client.put(
                        f"{_connections_url()}/{connection_id}",
                        headers=await _auth_headers(),
                        json={"attributes": {}, "parameters": {"hostname": hostname}},
                    )
                    response.raise_for_status()
                    return {"method": "PUT (fallback)", "status": "success", "response": response.json() if response.text else {}}
            else:
                raise


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