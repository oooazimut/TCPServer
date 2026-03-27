import os
from datetime import datetime

import aiosqlite
import pytest

from domain.entities import Record
from infra.repo.sqlite_repo import SQLiteRepo, init_db


@pytest.fixture
async def repo(tmp_path):
    path = str(tmp_path / "test.db")
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await init_db(db)
    repo = SQLiteRepo(db)
    yield repo
    await db.close()


class TestSQLiteRepo:
    @pytest.mark.asyncio
    async def test_init_db(self, tmp_path):
        path = str(tmp_path / "test.db")
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await init_db(db)
        assert os.path.exists(path)
        await db.close()

    @pytest.mark.asyncio
    async def test_add(self, repo):
        record = Record(name="test", value=1.5, dttm=datetime.now())
        row_id = await repo.add(record)

        assert row_id is not None

        result = await repo.get()
        assert result.name == "test"
        assert result.value == 1.5

    @pytest.mark.asyncio
    async def test_get_empty(self, repo):
        result = await repo.get()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_list(self, repo):
        records = [
            Record(name="a", value=1.0, dttm=datetime.now()),
            Record(name="b", value=2.0, dttm=datetime.now()),
        ]
        await repo.add_list(records)

        result = await repo.get_list()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_list_preserves_insert_order(self, repo):
        records = [
            Record(name="first", value=1.0, dttm=datetime.now()),
            Record(name="second", value=2.0, dttm=datetime.now()),
        ]
        await repo.add_list(records)

        result = await repo.get_list()

        assert [record.name for record in result] == ["first", "second"]

    @pytest.mark.asyncio
    async def test_get_by_name(self, repo):
        records = [
            Record(name="sensor1", value=1.0, dttm=datetime.now()),
            Record(name="sensor1", value=2.0, dttm=datetime.now()),
            Record(name="sensor2", value=3.0, dttm=datetime.now()),
        ]
        await repo.add_list(records)

        result = await repo.get_by_name("sensor1")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_name_returns_empty_list_for_missing_name(self, repo):
        result = await repo.get_by_name("missing")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_name_preserves_insert_order(self, repo):
        records = [
            Record(name="sensor1", value=1.0, dttm=datetime.now()),
            Record(name="sensor1", value=2.0, dttm=datetime.now()),
            Record(name="sensor1", value=3.0, dttm=datetime.now()),
        ]
        await repo.add_list(records)

        result = await repo.get_by_name("sensor1")

        assert [record.value for record in result] == [1.0, 2.0, 3.0]

    @pytest.mark.asyncio
    async def test_add_list(self, repo):
        records = [
            Record(name="a", value=1.0, dttm=datetime.now()),
            Record(name="b", value=2.0, dttm=datetime.now()),
        ]
        await repo.add_list(records)

        result = await repo.get_list()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_add_list_empty(self, repo):
        await repo.add_list([])

        result = await repo.get_list()

        assert result == []