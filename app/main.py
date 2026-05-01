import os

from dotenv import load_dotenv
from fastapi import FastAPI

from app.routers import users, workspaces

load_dotenv()

APP_TITLE = os.getenv("APP_TITLE", "Guacamole Wrapper API")

app = FastAPI(title=APP_TITLE)

app.include_router(users.router)
app.include_router(workspaces.router)


@app.get("/")
async def root():
    return {"message": "Broker running"}