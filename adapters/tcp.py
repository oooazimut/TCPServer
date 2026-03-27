import json
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass
from typing import Any, List

from domain.use_cases import GetRecordsRequest, PostRecordsRequest

from adapters.exceptions import IncompleteRequestError, InvalidRequestError
from adapters.presenter import Presenter
from adapters.retry import retry_async

STOP_CHAR = "$"


@dataclass(frozen=True)
class ParsedData:
    command: str
    request: PostRecordsRequest | GetRecordsRequest


class TCPReceiver:
    @retry_async(max_attempts=3, delay=0.5, exceptions=(ConnectionError,))
    async def receive(self, reader: StreamReader) -> str | None:
        buffer = ""

        while True:
            chunk = await reader.read(1024)
            if not chunk:
                if buffer.strip():
                    raise IncompleteRequestError
                return None

            buffer += chunk.decode()

            if STOP_CHAR in buffer:
                buffer = buffer[: buffer.index(STOP_CHAR)]
                break

        buffer = buffer.strip()
        if not buffer:
            return None

        return buffer


class Parser:
    def parse_request(self, raw_data: str | None) -> ParsedData:
        if not raw_data:
            raise InvalidRequestError

        parts = raw_data.split("|", 1)
        if len(parts) != 2:
            raise InvalidRequestError

        command = parts[0].strip().lower()
        payload = parts[1].strip()

        if not command or not payload:
            raise InvalidRequestError

        match command:
            case "get":
                return ParsedData(
                    command=command,
                    request=GetRecordsRequest(
                        names=self._parse_names(payload)
                    ),
                )

            case "post":
                return ParsedData(
                    command=command,
                    request=PostRecordsRequest(
                        raw_records=self._parse_raw_records(payload)
                    ),
                )

        raise InvalidRequestError

    def _parse_names(self, payload: str) -> List[str]:
        return [name.strip() for name in payload.split(",")]

    def _parse_raw_records(self, payload: str) -> List[tuple[str, float]]:
        raw_records = []
        for record in payload.split(","):
            parts = record.split(":")
            if len(parts) != 2:
                continue
            name = parts[0].strip()
            value = self._to_float(parts[1].strip())
            raw_records.append((name, value))
        return raw_records

    def _to_float(self, data: str) -> float:
        try:
            return float(data)
        except ValueError:
            return 0.0


class TCPTransmitter:
    def __init__(self, presenter: Presenter) -> None:
        self.presenter = presenter

    async def transmit(self, writer: StreamWriter, data: Any) -> None:
        response = json.dumps(self.presenter.present(data), ensure_ascii=False) + STOP_CHAR
        writer.write(response.encode())
        await writer.drain()
