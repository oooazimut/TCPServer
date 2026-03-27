import asyncio
import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.use_cases import GetRecordsRequest, GetRecordsResult, PostRecordsRequest, SaveRecordsResult
from infra.tcp_adapters.receiver import InvalidRequestError
from server import App, build_app


@dataclass(frozen=True)
class ParsedCommandStub:
    name: str
    request: PostRecordsRequest | GetRecordsRequest


class TestApp:
    @pytest.mark.asyncio
    async def test_handler_transmits_save_use_case_response(self):
        receiver = MagicMock()
        receiver.receive = AsyncMock(return_value="POST|sensor1|25.5")
        receiver.parse_request = MagicMock(
            return_value=ParsedCommandStub(
                name="post",
                request=PostRecordsRequest(records=[("sensor1", 25.5)]),
            )
        )

        transmitter = MagicMock()
        transmitter.transmit = AsyncMock()

        save_records_use_case = MagicMock()
        save_records_use_case.execute = AsyncMock(return_value=SaveRecordsResult(saved=1))

        get_records_use_case = MagicMock()
        get_records_use_case.execute = AsyncMock()

        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        app = App(receiver, transmitter, save_records_use_case, get_records_use_case)
        await app.handler(MagicMock(), writer)

        save_records_use_case.execute.assert_awaited_once_with(
            PostRecordsRequest(records=[("sensor1", 25.5)])
        )
        get_records_use_case.execute.assert_not_called()
        transmitter.transmit.assert_awaited_once_with(writer, SaveRecordsResult(saved=1))
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handler_transmits_get_use_case_response(self):
        receiver = MagicMock()
        receiver.receive = AsyncMock(return_value="GET|sensor1")
        receiver.parse_request = MagicMock(
            return_value=ParsedCommandStub(
                name="get",
                request=GetRecordsRequest(name="sensor1"),
            )
        )

        transmitter = MagicMock()
        transmitter.transmit = AsyncMock()

        save_records_use_case = MagicMock()
        save_records_use_case.execute = AsyncMock()
        get_records_use_case = MagicMock()
        get_records_use_case.execute = AsyncMock(return_value=GetRecordsResult(records=[]))

        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        app = App(receiver, transmitter, save_records_use_case, get_records_use_case)
        await app.handler(MagicMock(), writer)

        get_records_use_case.execute.assert_awaited_once_with(GetRecordsRequest(name="sensor1"))
        save_records_use_case.execute.assert_not_called()
        transmitter.transmit.assert_awaited_once_with(writer, GetRecordsResult(records=[]))
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handler_transmits_invalid_request_response(self):
        receiver = MagicMock()
        receiver.receive = AsyncMock(return_value="invalid")
        receiver.parse_request = MagicMock(side_effect=InvalidRequestError())

        transmitter = MagicMock()
        transmitter.transmit = AsyncMock()

        app = App(receiver, transmitter, MagicMock(), MagicMock())

        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        await app.handler(MagicMock(), writer)

        transmitter.transmit.assert_awaited_once()
        transmitted_error = transmitter.transmit.await_args.args[1]
        assert isinstance(transmitted_error, InvalidRequestError)
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handler_transmits_error_response_on_exception(self):
        receiver = MagicMock()
        receiver.receive = AsyncMock(side_effect=RuntimeError("boom"))

        transmitter = MagicMock()
        transmitter.transmit = AsyncMock()

        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        app = App(receiver, transmitter, MagicMock(), MagicMock())
        await app.handler(MagicMock(), writer)

        transmitter.transmit.assert_awaited_once()
        transmitted_error = transmitter.transmit.await_args.args[1]
        assert isinstance(transmitted_error, RuntimeError)
        assert str(transmitted_error) == "boom"
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_build_app_returns_app_instance(self, tmp_path):
        db_path = str(tmp_path / "test.db")

        async with build_app(db_path) as app:
            assert isinstance(app, App)
            assert app.receiver is not None
            assert app.transmitter is not None
            assert app.save_records_use_case is not None
            assert app.get_records_use_case is not None

    @pytest.mark.asyncio
    async def test_end_to_end_post_then_get(self, tmp_path):
        db_path = str(tmp_path / "test.db")

        async with build_app(db_path) as app:
            server = await asyncio.start_server(app.get_handler(), host="127.0.0.1", port=0)
            host, port = server.sockets[0].getsockname()

            async with server:
                reader, writer = await asyncio.open_connection(host, port)
                writer.write(b"POST|sensor1|25.5$")
                await writer.drain()
                response = await reader.readuntil(b"$")
                writer.close()
                await writer.wait_closed()

                post_result = json.loads(response[:-1].decode())
                assert post_result == {"status": "ok", "saved": 1}

                reader, writer = await asyncio.open_connection(host, port)
                writer.write(b"GET|sensor1$")
                await writer.drain()
                response = await reader.readuntil(b"$")
                writer.close()
                await writer.wait_closed()

                get_result = json.loads(response[:-1].decode())
                assert len(get_result) == 1
                assert get_result[0]["name"] == "sensor1"
                assert get_result[0]["value"] == 25.5