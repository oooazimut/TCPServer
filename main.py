import asyncio
import logging
import signal

from config import settings
from server import build_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GracefulShutdown:
    def __init__(self) -> None:
        self.shutdown_event = asyncio.Event()

    def signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()


async def main() -> None:
    shutdown = GracefulShutdown()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown.signal_handler, sig, None)

    async with build_app() as app:
        server = await asyncio.start_server(app.get_handler(), host=settings.host, port=settings.port)
        addr = server.sockets[0].getsockname()
        logger.info("Сервер запущен: %s", addr)

        async with server:
            await shutdown.shutdown_event.wait()


if __name__ == "__main__":
    asyncio.run(main())
