from asyncio import StreamReader
from dataclasses import dataclass

from domain.use_cases import GetRecordsRequest, PostRecordsRequest

STOP_CHAR = "$"


class InvalidRequestError(Exception):
    pass


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    request: PostRecordsRequest | GetRecordsRequest


class TCPReceiver:
    async def receive(self, reader: StreamReader) -> str | None:
        buffer = ""

        while True:
            chunk = await reader.read(1024)
            if not chunk:
                return None

            buffer += chunk.decode()

            if STOP_CHAR in buffer:
                buffer = buffer[: buffer.index(STOP_CHAR)]
                break

        buffer = buffer.strip()
        if not buffer:
            return None

        return buffer

    def parse_request(self, raw_data: str | None) -> ParsedCommand:
        if not raw_data:
            raise InvalidRequestError

        parts = raw_data.split("|", 1)
        if len(parts) != 2:
            raise InvalidRequestError

        command = parts[0].strip().lower()
        payload = parts[1].strip()

        if not command or not payload:
            raise InvalidRequestError

        if command == "get":
            return ParsedCommand(name=command, request=GetRecordsRequest(name=payload))

        if command == "post":
            records: list[tuple[str, float]] = []
            for item in payload.split(","):
                record_parts = item.split("|")
                if len(record_parts) != 2:
                    continue

                name = record_parts[0].strip()
                try:
                    value = float(record_parts[1].strip())
                except ValueError:
                    value = 0.0

                records.append((name, value))

            return ParsedCommand(name=command, request=PostRecordsRequest(records=records))

        raise InvalidRequestError