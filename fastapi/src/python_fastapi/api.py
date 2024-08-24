import multiprocessing
import platform
import sqlite3

import aiofiles
import psutil
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sqlite_db: str | None = "db.sqlite"


app = FastAPI()
settings = Settings()
sql_conn = sqlite3.connect(settings.sqlite_db)


def init_db():
    cursor = sql_conn.cursor()

    # Enable WAL mode
    cursor.execute("PRAGMA journal_mode = WAL;")

    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)


init_db()


class BaseAPIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class InfoResponse(BaseAPIModel):
    cpu_count: int = Field(..., description="Number of CPUs", alias="cpuCount")
    cpu_model: str = Field(..., description="CPU Model", alias="cpuModel")
    cpu_load: str = Field(..., description="CPU Load", alias="cpuLoad")
    os_info: str = Field(..., description="OS Information", alias="osInfo")
    ram_capacity: str = Field(..., description="RAM Capacity", alias="ramCapacity")
    ram_usage: str = Field(..., description="RAM Usage", alias="ramUsage")


def execute_benchmark() -> int:
    pass


@app.get(
    "/index.html",
    description="Get the index page",
    tags=["Static Files"],
    response_class=HTMLResponse,
)
async def get_index():
    async with aiofiles.open("static/index.html", mode="r") as f:
        return await f.read()


@app.get(
    "/server-info",
    description="Get the server information",
    tags=["Info"],
    response_model=InfoResponse,
)
async def get_info():
    ram_capacity = psutil.virtual_memory().total / 1024 / 1024 / 1024
    return InfoResponse(
        cpu_count=multiprocessing.cpu_count(),
        cpu_model=platform.processor(),
        cpu_load=str(psutil.cpu_percent()),
        os_info=platform.platform(),
        ram_usage=str(f"{psutil.virtual_memory().percent}%"),
        ram_capacity=str(f"{ram_capacity:.1f} GB"),
    )
