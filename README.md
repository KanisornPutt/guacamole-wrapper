# Guacamole Wrapper

FastAPI service that stores wrapper state in Postgres and provisions users,
connections, and permissions through the Apache Guacamole REST API.

## Requirements
- Python 3.10+
- PostgreSQL
- Reachable Apache Guacamole instance

## Setup
1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in the values.

## Database
- Create the database, for example: `createdb wrapper_db`
- Run migrations with `alembic upgrade head`
- Create a new migration after model changes with `alembic revision --autogenerate -m "describe change"`

## Run
- Start the API with `uvicorn app.main:app --reload`

## Docker
- Build the image with `docker build -t kanisornp/guacamole-wrapper:v.1 .`
- The compose file uses the app image name `kanisornp/guacamole-wrapper:v.1` and includes Postgres

## API
- Root: `GET /`
- Users: `POST /users/`
- Workspaces: `POST /workspaces/`
- Workspace network: `PATCH /workspaces/{external_instance_id}/network`
- Workspace delete: `DELETE /workspaces/{external_instance_id}`

## OpenAPI
- Static spec: `openapi.json`
- Interactive docs are available from FastAPI at `/docs` and `/openapi.json`

## Notes
- Configuration is loaded from `.env`.
- Guacamole login uses the configured Guacamole username/password to fetch an auth token per request.
- If the API runs on your host and Guacamole runs in Docker, set `GUACAMOLE_BASE_URL` to the published URL, for example `http://localhost:8080/guacamole/api`.
