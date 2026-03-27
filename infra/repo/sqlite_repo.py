import logging
from contextlib import asynccontextmanager
from datetime import datetime

import aiosqlite

from domain.entities import Record
from domain.ports import Repo

logger = logging.getLogger(__name__)

DB_PATH = "records.db"


@asynccontextmanager
async def get_db(db_path: str = DB_PATH):
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value REAL NOT NULL,
            dttm TEXT NOT NULL
        )
    """
    )
    await db.commit()


class SQLiteRepo(Repo):
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db: aiosqlite.Connection = db

    async def add(self, data: Record) -> int | None:
        cursor = await self._db.execute(
            "INSERT INTO records (name, value, dttm) VALUES (?, ?, ?)",
            (data.name, data.value, data.dttm.isoformat()),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get(self) -> Record | None:
        cursor = await self._db.execute(
            "SELECT name, value, dttm FROM records ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if row:
            return Record(
                name=row["name"],
                value=row["value"],
                dttm=datetime.fromisoformat(row["dttm"]),
            )
        return None

    async def get_list(self) -> list[Record]:
        cursor = await self._db.execute(
            "SELECT name, value, dttm FROM records ORDER BY id"
        )
        rows = await cursor.fetchall()
        return [
            Record(
                name=row["name"],
                value=row["value"],
                dttm=datetime.fromisoformat(row["dttm"]),
            )
            for row in rows
        ]

    async def get_by_name(self, name: str) -> list[Record]:
        cursor = await self._db.execute(
            "SELECT name, value, dttm FROM records WHERE name = ? ORDER BY id", (name,)
        )
        rows = await cursor.fetchall()
        return [
            Record(
                name=row["name"],
                value=row["value"],
                dttm=datetime.fromisoformat(row["dttm"]),
            )
            for row in rows
        ]

    async def add_list(self, data: list[Record]) -> None:
        await self._db.executemany(
            "INSERT INTO records (name, value, dttm) VALUES (?, ?, ?)",
            [(record.name, record.value, record.dttm.isoformat()) for record in data],
        )
        await self._db.commit()
