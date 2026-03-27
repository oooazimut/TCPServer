from datetime import datetime

import pytest

from domain.entities import Record
from domain.use_cases import (
    GetRecordsRequest,
    GetRecordsResult,
    GetRecordsUseCase,
    NoDataToSaveError,
    PostRecordsRequest,
    SaveRecordsResult,
    SaveRecordsUseCase,
)


class MockRepo:
    def __init__(self):
        self.storage = []

    async def add(self, data):
        self.storage.append(data)

    async def get(self):
        return self.storage[-1] if self.storage else None

    async def get_list(self):
        return self.storage.copy()

    async def add_list(self, data):
        self.storage.extend(data)

    async def get_by_name(self, name):
        return [record for record in self.storage if record.name == name]


class FixedClock:
    def __init__(self, current: datetime):
        self._current = current

    def now(self) -> datetime:
        return self._current


class TestSaveRecordsUseCase:
    @pytest.mark.asyncio
    async def test_execute_saves_records(self):
        repo = MockRepo()
        clock = FixedClock(datetime(2024, 1, 1, 12, 0, 0))
        use_case = SaveRecordsUseCase(repo, clock)

        result = await use_case.execute(
            PostRecordsRequest(records=[("sensor1", 25.5), ("sensor2", 30.0)])
        )

        assert result == SaveRecordsResult(saved=2)
        assert len(repo.storage) == 2
        assert repo.storage[0].dttm == datetime(2024, 1, 1, 12, 0, 0)

    @pytest.mark.asyncio
    async def test_execute_raises_when_no_data(self):
        repo = MockRepo()
        clock = FixedClock(datetime(2024, 1, 1, 12, 0, 0))
        use_case = SaveRecordsUseCase(repo, clock)

        with pytest.raises(NoDataToSaveError):
            await use_case.execute(PostRecordsRequest(records=[]))


class TestGetRecordsUseCase:
    @pytest.mark.asyncio
    async def test_execute_returns_records(self):
        repo = MockRepo()
        repo.storage = [
            Record(name="test", value=1.0, dttm=datetime(2024, 1, 1, 12, 0, 0)),
            Record(name="test", value=2.0, dttm=datetime(2024, 1, 1, 12, 1, 0)),
        ]
        use_case = GetRecordsUseCase(repo)

        result = await use_case.execute(GetRecordsRequest(name="test"))

        assert result == GetRecordsResult(records=repo.storage)

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list_for_unknown_name(self):
        use_case = GetRecordsUseCase(MockRepo())

        result = await use_case.execute(GetRecordsRequest(name="missing"))

        assert result == GetRecordsResult(records=[])
