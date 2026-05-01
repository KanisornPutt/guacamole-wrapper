# Guacamole Wrapper

## Prerequisites
- Python 3.10+
- Postgres
- Apache Guacamole API reachable from this service

## Setup
1) Create and activate a virtual environment
2) Install dependencies:
   - `pip install -r requirements.txt`

3) Create a `.env` file from `.env.example` and fill in values.

## Database (Alembic)
- Create the database (example):
  - `createdb wrapper_db`

- Run migrations:
  - `alembic upgrade head`

- Generate new migrations after model changes:
  - `alembic revision --autogenerate -m "describe change"`

## Run the API
- `uvicorn app.main:app --reload`

## Notes
- The API loads configuration from `.env`.
- Guacamole access uses username/password to retrieve an auth token per request.
- If the API runs on your host and Guacamole is in Docker, set `GUACAMOLE_BASE_URL` to the published host URL (e.g. `http://localhost:8080/guacamole/api`).
