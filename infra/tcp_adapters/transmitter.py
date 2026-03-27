import json
from asyncio import StreamWriter
from typing import Any

from domain.entities import Record
from domain.use_cases import GetRecordsResult, NoDataToSaveError, SaveRecordsResult
from infra.tcp_adapters.receiver import InvalidRequestError

STOP_CHAR = "$"


class TCPTransmitter:
    async def transmit(self, writer: StreamWriter, data: Any) -> None:
        response = json.dumps(self.present(data), ensure_ascii=False) + STOP_CHAR
        writer.write(response.encode())
        await writer.drain()

    def present(self, data: Any) -> dict[str, Any] | list[dict[str, Any]]:
        if isinstance(data, SaveRecordsResult):
            return {"status": "ok", "saved": data.saved}

        if isinstance(data, GetRecordsResult):
            return [self._present_record(record) for record in data.records]

        if isinstance(data, InvalidRequestError):
            return {"error": "invalid request"}

        if isinstance(data, NoDataToSaveError):
            return {"error": "no data to save"}

        if isinstance(data, Exception):
            return {"error": str(data)}

        return data

    def _present_record(self, record: Record) -> dict[str, str | float]:
        return {
            "name": record.name,
            "value": record.value,
            "dttm": record.dttm.isoformat(),
        }
