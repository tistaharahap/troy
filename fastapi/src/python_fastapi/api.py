import multiprocessing
import platform
import sqlite3
import time
from random import sample
from secrets import token_hex
from sqlite3 import Cursor, Connection
from typing import Tuple

import aiofiles
import asyncer
import psutil
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sqlite_db: str | None = "db.sqlite"

    # Benchmark
    benchmark_runs: int | None = 1_000
    chunk_size: int | None = 50


app = FastAPI()
settings = Settings()


def init_db() -> Tuple[Connection, Cursor, str]:
    """
    Initialize the Sqlite DB for the benchmark
    :return: Tuple[Connection, Cursor, str] - A tuple of the SQLite connection, cursor and created table name.
    """
    sql_conn = sqlite3.connect(settings.sqlite_db)

    cursor = sql_conn.cursor()

    # Enable WAL mode
    cursor.execute("PRAGMA journal_mode = WAL;")

    # Create table if not exists
    table_name = token_hex(23)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS '{table_name}' (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            content TEXT NOT NULL
        );
    """)

    return sql_conn, cursor, table_name


def run_benchmark() -> Tuple[float, float, float, float, float]:
    """
    Run the benchmark to read and write from an SQLite database.
    :return: Tuple[float, float, float, float, float] - A tuple of the elapsed time, write time delta, writes per
    second, read time delta and reads per second.
    """
    start_time = time.process_time()

    # Write benchmark
    sql_conn, cursor, table_name = init_db()
    row_ids = []
    write_count = 0
    failed_write_count = 0
    insert_query = "INSERT INTO '{table_name}' (author, content) VALUES ('{author}', '{content}')"
    for i in range(settings.benchmark_runs):
        values = []
        for j in range(settings.chunk_size):
            values.append([token_hex(23), token_hex(23)])

        cursor.execute("BEGIN TRANSACTION;")
        for author, content in values:
            sql = insert_query.format(author=author, content=content, table_name=table_name)
            try:
                cursor.execute(sql)
                write_count += 1
                row_ids.append(cursor.lastrowid)
            except Exception:
                failed_write_count += 1

        cursor.execute("COMMIT;")
        i += settings.chunk_size

    # Record write delta
    write_time_delta = time.process_time() - start_time
    writes_per_second = write_count / write_time_delta

    # Read benchmark
    read_count = 0
    read_sample_size = min(10_000, len(row_ids))
    random_ids = sample(row_ids, read_sample_size)
    read_query = "SELECT * FROM '{table_name}' WHERE id = {row_id}"
    read_start_time = time.process_time()
    for row_id in random_ids:
        sql = read_query.format(row_id=row_id, table_name=table_name)
        cursor.execute(sql)
        read_count += 1

    read_time_delta = time.process_time() - read_start_time
    reads_per_second = read_count / read_time_delta

    elapsed_time = time.process_time() - start_time

    # Delete table and close connection
    cursor.execute(f"DROP TABLE IF EXISTS '{table_name}';")
    sql_conn.close()

    return elapsed_time, write_time_delta, writes_per_second, read_time_delta, reads_per_second


class BaseAPIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class InfoResponse(BaseAPIModel):
    cpu_count: int = Field(..., description="Number of CPUs", alias="cpuCount")
    cpu_model: str = Field(..., description="CPU Model", alias="cpuModel")
    cpu_load: str = Field(..., description="CPU Load", alias="cpuLoad")
    os_info: str = Field(..., description="OS Information", alias="osInfo")
    ram_capacity: str = Field(..., description="RAM Capacity", alias="ramCapacity")
    ram_usage: str = Field(..., description="RAM Usage", alias="ramUsage")


class BenchmarkResponse(BaseAPIModel):
    elapsed_time: float = Field(..., description="Benchmark elapsed time", alias="elapsedTime")
    write_time_delta: float = Field(..., description="Benchmark write time", alias="writeTimeDelta")
    writes_per_second: float = Field(..., description="Benchmark write per second", alias="writesPerSecond")
    read_time_delta: float = Field(..., description="Benchmark read time", alias="readTimeDelta")
    reads_per_second: float = Field(..., description="Benchmark read per second", alias="readsPerSecond")


async def execute_benchmark() -> Tuple[float, float, float, float, float]:
    """
    Wrapper to run the synchronous benchmark in an asynchronous context.
    :return: Tuple[float, float, float, float, float] - A tuple of the elapsed time, write time delta, writes per
    second, read time delta and reads per second.
    """
    return await asyncer.asyncify(run_benchmark)()


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


@app.get(
    "/benchmark",
    description="Run the benchmark",
    tags=["Benchmark"],
    response_model=BenchmarkResponse,
)
async def benchmark():
    elapsed_time, write_time_delta, writes_per_second, read_time_delta, reads_per_second = await execute_benchmark()
    return BenchmarkResponse(
        elapsed_time=elapsed_time,
        write_time_delta=write_time_delta,
        writes_per_second=writes_per_second,
        read_time_delta=read_time_delta,
        reads_per_second=reads_per_second,
    )
