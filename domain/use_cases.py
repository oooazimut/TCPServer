from dataclasses import dataclass
from typing import List

from domain.entities import Record
from domain.ports import Clock, Repo


@dataclass(frozen=True)
class PostRecordsRequest:
    raw_records: List[tuple[str, float]]


@dataclass(frozen=True)
class GetRecordsRequest:
    names: List[str]


@dataclass(frozen=True)
class SaveRecordsResult:
    saved: int


@dataclass(frozen=True)
class GetRecordsResult:
    records: list[Record]


class NoDataToSaveError(Exception):
    pass


class SaveRecordsUseCase:
    def __init__(self, repo: Repo, clock: Clock) -> None:
        self.repo = repo
        self.clock = clock

    async def execute(self, request: PostRecordsRequest) -> SaveRecordsResult:
        if not request.raw_records:
            raise NoDataToSaveError

        records = [
            Record(name=name, value=value, dttm=self.clock.now())
            for name, value in request.raw_records
        ]
        await self.repo.add_list(records)
        return SaveRecordsResult(saved=len(records))


class GetRecordsUseCase:
    def __init__(self, repo: Repo) -> None:
        self.repo = repo

    async def execute(self, request: GetRecordsRequest) -> GetRecordsResult:
        records = []
        for name in request.names:
            records.extend(await self.repo.get_by_name(name))
        return GetRecordsResult(records=records)


class ProcessRequestUseCase:
    def __init__(
        self,
        save_records_use_case: SaveRecordsUseCase,
        get_records_use_case: GetRecordsUseCase,
    ) -> None:
        self.save_records_use_case = save_records_use_case
        self.get_records_use_case = get_records_use_case

    async def execute(self, request: PostRecordsRequest | GetRecordsRequest) -> SaveRecordsResult | GetRecordsResult:
        if isinstance(request, PostRecordsRequest):
            return await self.save_records_use_case.execute(request)
        else:
            return await self.get_records_use_case.execute(request)
