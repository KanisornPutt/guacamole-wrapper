# Guacamole Wrapper

FastAPI service that stores workspace state in PostgreSQL and provisions users,
connections, and permissions through the Apache Guacamole REST API.

## Overview

The API is organized into two routers:

- `/users` for creating Guacamole-backed users
- `/workspaces` for creating workspaces and managing their network assignment

The service also exposes the default FastAPI docs at `/docs` and `/openapi.json`.

## Requirements

- Python 3.10+
- PostgreSQL
- Reachable Apache Guacamole instance

## Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Create a `.env` file with the required database and Guacamole settings.
4. Run migrations with `alembic upgrade head`.

Required environment variables:

- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `GUACAMOLE_BASE_URL`
- `GUACAMOLE_DATA_SOURCE`
- `GUACAMOLE_USERNAME`
- `GUACAMOLE_PASSWORD`
- `GUACAMOLE_NEW_USER_PASSWORD`

Common optional settings:

- `APP_TITLE`
- `DB_DIALECT`
- `DB_HOST`
- `DB_PORT`
- `SQLALCHEMY_ECHO`
- `GUACAMOLE_SSH_USERNAME`
- `GUACAMOLE_SSH_PASSWORD`
- `GUACAMOLE_SSH_PORT`
- `GUACAMOLE_HTTP_TIMEOUT`

You can alternatively provide `DATABASE_URL` instead of the `DB_*` variables.

If you need a fresh migration after changing models, use:

```bash
alembic revision --autogenerate -m "describe change"
```

## Run

Start the API with:

```bash
uvicorn app.main:app --reload
```

The root endpoint returns:

```json
{ "message": "Broker running" }
```

## Data Models

### `UserCreate`

```json
{
	"external_user_id": "string",
	"username": "string"
}
```

### `WorkspaceCreate`

```json
{
	"external_instance_id": "string",
	"external_user_id": "string",
	"username": "string",
	"workspace_name": "string",
	"os_username": "string",
	"os_password": "string"
}
```

`username`, `os_username`, and `os_password` are optional in the schema, but `username` is required when the referenced user does not already exist.

### `NetworkAssign` / `NetworkDisassociate`

```json
{
	"floating_ip": "string"
}
```

## API Endpoints

### `GET /`

Health-style root response.

### `POST /users/`

Creates a user in Guacamole and stores it locally.

Behavior:

- Returns `{ "status": "exists" }` if the `external_user_id` already exists
- Returns `{ "status": "created" }` after creating the user

### `POST /workspaces/`

Creates a workspace record and ensures the user exists first.

Behavior:

- Returns `{ "status": "exists" }` if the workspace already exists
- Returns `{ "status": "created" }` after the workspace is stored
- If the user is missing locally, `username` must be provided so the API can create the user

### `PATCH /workspaces/{external_instance_id}/network`

Assigns or updates a floating IP for a workspace and synchronizes the Guacamole connection.

Request body:

```json
{ "floating_ip": "203.0.113.10" }
```

Behavior:

- Creates a Guacamole connection the first time a workspace gets a floating IP
- Reuses and updates the existing Guacamole connection on later calls
- Persists `guacamole_connection_id`, `guacamole_group_id`, and `floating_ip`
- Re-grants user and connection-group permissions as needed

Typical response:

```json
{
	"status": "updated",
	"create_connection": {
		"identifier": 1,
		"connection_group_id": 2
	}
}
```

Additional fields may appear depending on whether a connection was created or updated, such as `create_user`, `update_connection`, and permission grant results.

### `DELETE /workspaces/network/disassociate`

Removes the Guacamole connection for the workspace that matches the provided floating IP and clears the IP locally.

Request body:

```json
{ "floating_ip": "203.0.113.10" }
```

Behavior:

- Returns `{ "status": "disassociated" }` when the workspace is found
- Deletes the Guacamole connection if one is linked
- Clears `floating_ip` and `guacamole_connection_id` in the database

### `DELETE /workspaces/{external_instance_id}`

Deletes a workspace and its Guacamole connection.

Behavior:

- Returns `{ "status": "deleted" }` when successful
- Removes the workspace record from the database

## Docker

- Build the image with `docker build -t kanisornp/guacamole-wrapper:v.1 .`
- `docker-compose.yml` starts the API with PostgreSQL

## Kubernetes

Kubernetes manifests are in the `k8s/` folder:

- `k8s/guacamole-wrapper-configmap.yaml` for non-secret settings
- `k8s/guacamole-wrapper-secret.yaml` for credentials and database URL
- `k8s/guacamole-wrapper-deployment.yaml` for the API deployment
- `k8s/guacamole-wrapper-service.yaml` for the cluster service

Update the ConfigMap and Secret values to match your cluster endpoints and credentials before applying.

## Notes

- Configuration is loaded from `.env`.
- Guacamole credentials are used to fetch an auth token per request.
- If the API runs on your host and Guacamole runs in Docker, set `GUACAMOLE_BASE_URL` to the published URL, for example `http://localhost:8080/guacamole/api`.
