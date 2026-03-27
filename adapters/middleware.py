import logging
from asyncio import StreamReader, StreamWriter
from collections.abc import Awaitable, Callable

from adapters.exceptions import InvalidRequestError
from adapters.presenter import Presenter
from adapters.tcp import Parser, TCPReceiver, TCPTransmitter

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware:
    def __init__(
        self,
        receiver: TCPReceiver,
        parser: Parser,
        transmitter: TCPTransmitter,
        presenter: Presenter,
    ) -> None:
        self.receiver = receiver
        self.parser = parser
        self.transmitter = transmitter
        self.presenter = presenter

    async def handle(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        next_handler: Callable[[StreamReader, StreamWriter], Awaitable[None]],
    ) -> None:
        try:
            await next_handler(reader, writer)
        except InvalidRequestError as error:
            await self.transmitter.transmit(writer, error)
        except Exception as error:
            logger.exception("Ошибка при обработке TCP-запроса")
            await self.transmitter.transmit(writer, error)
        finally:
            writer.close()
            await writer.wait_closed()
