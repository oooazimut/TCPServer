import json
from datetime import datetime

import pytest

from domain.entities import Record
from domain.use_cases import GetRecordsResult, NoDataToSaveError, SaveRecordsResult
from infra.tcp_adapters.receiver import InvalidRequestError
from infra.tcp_adapters.transmitter import STOP_CHAR, TCPTransmitter


class FakeWriter:
    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data

    async def drain(self):
        pass


class TestTCPTransmitter:
    @pytest.mark.asyncio
    async def test_transmit_save_result(self):
        writer = FakeWriter()
        transmitter = TCPTransmitter()

        await transmitter.transmit(writer, SaveRecordsResult(saved=2))

        result = json.loads(writer.data[:-1].decode())
        assert result == {"status": "ok", "saved": 2}

    @pytest.mark.asyncio
    async def test_transmit_get_result(self):
        writer = FakeWriter()
        transmitter = TCPTransmitter()

        payload = GetRecordsResult(
            records=[
                Record(name="sensor1", value=25.5, dttm=datetime(2024, 1, 1, 12, 0, 0)),
                Record(name="sensor2", value=30.0, dttm=datetime(2024, 1, 1, 12, 1, 0)),
            ]
        )
        await transmitter.transmit(writer, payload)

        result = json.loads(writer.data[:-1].decode())
        assert len(result) == 2
        assert result[0]["name"] == "sensor1"
        assert result[0]["value"] == 25.5

    @pytest.mark.asyncio
    async def test_transmit_invalid_request_error(self):
        writer = FakeWriter()
        transmitter = TCPTransmitter()

        await transmitter.transmit(writer, InvalidRequestError())

        result = json.loads(writer.data[:-1].decode())
        assert result == {"error": "invalid request"}

    @pytest.mark.asyncio
    async def test_transmit_no_data_to_save_error(self):
        writer = FakeWriter()
        transmitter = TCPTransmitter()

        await transmitter.transmit(writer, NoDataToSaveError())

        result = json.loads(writer.data[:-1].decode())
        assert result == {"error": "no data to save"}

    @pytest.mark.asyncio
    async def test_transmit_adds_stop_char(self):
        writer = FakeWriter()
        transmitter = TCPTransmitter()

        await transmitter.transmit(writer, SaveRecordsResult(saved=1))

        assert writer.data.endswith(STOP_CHAR.encode())
