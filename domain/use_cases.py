from dataclasses import dataclass

from domain.entities import Record
from domain.ports import Clock, Repo


@dataclass(frozen=True)
class PostRecordsRequest:
    records: list[tuple[str, float]]


@dataclass(frozen=True)
class GetRecordsRequest:
    name: str


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
        if not request.records:
            raise NoDataToSaveError

        records = [
            Record(name=name, value=value, dttm=self.clock.now())
            for name, value in request.records
        ]
        await self.repo.add_list(records)
        return SaveRecordsResult(saved=len(records))


class GetRecordsUseCase:
    def __init__(self, repo: Repo) -> None:
        self.repo = repo

    async def execute(self, request: GetRecordsRequest) -> GetRecordsResult:
        records = await self.repo.get_by_name(request.name)
        return GetRecordsResult(records=records)
