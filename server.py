from asyncio import StreamReader, StreamWriter
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from config import settings
from domain.ports import Clock
from domain.use_cases import GetRecordsUseCase, ProcessRequestUseCase, SaveRecordsUseCase
from adapters.middleware import ErrorHandlerMiddleware
from adapters.presenter import Presenter
from adapters.tcp import Parser, TCPReceiver, TCPTransmitter
from infra.clock import SystemClock
from infra.repo.sqlite_repo import SQLiteRepo, get_db, init_db


class App:
    def __init__(
        self,
        receiver: TCPReceiver,
        parser: Parser,
        transmitter: TCPTransmitter,
        process_request_use_case: ProcessRequestUseCase,
        middleware: ErrorHandlerMiddleware,
    ) -> None:
        self.receiver = receiver
        self.parser = parser
        self.transmitter = transmitter
        self.process_request_use_case = process_request_use_case
        self.middleware = middleware

    async def handler(self, reader: StreamReader, writer: StreamWriter) -> None:
        raw_data = await self.receiver.receive(reader)
        parsed = self.parser.parse_request(raw_data)

        response = await self.process_request_use_case.execute(parsed.request)

        await self.transmitter.transmit(writer, response)

    async def wrapped_handler(self, reader: StreamReader, writer: StreamWriter) -> None:
        await self.middleware.handle(reader, writer, self.handler)

    def get_handler(self) -> Callable[[StreamReader, StreamWriter], Awaitable[None]]:
        return self.wrapped_handler


@asynccontextmanager
async def build_app(db_path: str = None) -> AsyncIterator[App]:
    if db_path is None:
        db_path = settings.db_path
    async with get_db(db_path) as db:
        await init_db(db)
        repo = SQLiteRepo(db)

        receiver = TCPReceiver()
        parser = Parser()
        presenter = Presenter()
        transmitter = TCPTransmitter(presenter)
        middleware = ErrorHandlerMiddleware(receiver, parser, transmitter, presenter)
        clock: Clock = SystemClock()
        save_records_use_case = SaveRecordsUseCase(repo, clock)
        get_records_use_case = GetRecordsUseCase(repo)
        process_request_use_case = ProcessRequestUseCase(
            save_records_use_case, get_records_use_case
        )

        yield App(
            receiver, parser, transmitter, process_request_use_case, middleware
        )