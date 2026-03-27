import asyncio
import logging
from asyncio import StreamReader, StreamWriter
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime

from domain.ports import Clock
from domain.use_cases import GetRecordsUseCase, SaveRecordsUseCase
from infra.repo.sqlite_repo import SQLiteRepo, get_db, init_db
from infra.tcp_adapters.receiver import InvalidRequestError, TCPReceiver
from infra.tcp_adapters.transmitter import TCPTransmitter

HOST = "localhost"
PORT = 8686

logger = logging.getLogger(__name__)


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now()


class App:
    def __init__(
        self,
        receiver: TCPReceiver,
        transmitter: TCPTransmitter,
        save_records_use_case: SaveRecordsUseCase,
        get_records_use_case: GetRecordsUseCase,
    ) -> None:
        self.receiver = receiver
        self.transmitter = transmitter
        self.save_records_use_case = save_records_use_case
        self.get_records_use_case = get_records_use_case

    async def handler(self, reader: StreamReader, writer: StreamWriter) -> None:
        try:
            raw_data = await self.receiver.receive(reader)
            parsed = self.receiver.parse_request(raw_data)

            if parsed.name == "post":
                response = await self.save_records_use_case.execute(parsed.request)
            else:
                response = await self.get_records_use_case.execute(parsed.request)

            await self.transmitter.transmit(writer, response)
        except InvalidRequestError as error:
            await self.transmitter.transmit(writer, error)
        except Exception as error:
            logger.exception("Ошибка при обработке TCP-запроса")
            await self.transmitter.transmit(writer, error)
        finally:
            writer.close()
            await writer.wait_closed()

    def get_handler(self) -> Callable[[StreamReader, StreamWriter], Awaitable[None]]:
        return self.handler


@asynccontextmanager
async def build_app(db_path: str = "records.db") -> AsyncIterator[App]:
    async with get_db(db_path) as db:
        await init_db(db)
        repo = SQLiteRepo(db)

        receiver = TCPReceiver()
        transmitter = TCPTransmitter()
        clock = SystemClock()
        save_records_use_case = SaveRecordsUseCase(repo, clock)
        get_records_use_case = GetRecordsUseCase(repo)

        yield App(receiver, transmitter, save_records_use_case, get_records_use_case)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    async with build_app() as app:
        server = await asyncio.start_server(app.get_handler(), host=HOST, port=PORT)
        addr = server.sockets[0].getsockname()
        logger.info("Сервер запущен: %s", addr)

        async with server:
            await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())