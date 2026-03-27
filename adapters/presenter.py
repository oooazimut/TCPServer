from typing import Any

from domain.entities import Record
from domain.use_cases import GetRecordsResult, NoDataToSaveError, SaveRecordsResult

from adapters.exceptions import InvalidRequestError


class Presenter:
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
