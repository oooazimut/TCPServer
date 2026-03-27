import pytest

from domain.use_cases import GetRecordsRequest, PostRecordsRequest
from infra.tcp_adapters.receiver import InvalidRequestError, TCPReceiver


class FakeReader:
    def __init__(self, data: str):
        self._data = data.encode()
        self._pos = 0

    async def read(self, n):
        if self._pos >= len(self._data):
            return b""
        chunk = self._data[self._pos : self._pos + n]
        self._pos += n
        return chunk


class TestTCPReceiver:
    @pytest.mark.asyncio
    async def test_receive_returns_raw_payload(self):
        receiver = TCPReceiver()
        reader = FakeReader("GET|sensor1$")

        result = await receiver.receive(reader)

        assert result == "GET|sensor1"

    @pytest.mark.asyncio
    async def test_receive_post_payload(self):
        receiver = TCPReceiver()
        reader = FakeReader("POST|sensor1|25.5,sensor2|30.0$")

        result = await receiver.receive(reader)

        assert result == "POST|sensor1|25.5,sensor2|30.0"

    @pytest.mark.asyncio
    async def test_receive_empty_buffer(self):
        receiver = TCPReceiver()
        reader = FakeReader("")

        result = await receiver.receive(reader)

        assert result is None

    @pytest.mark.asyncio
    async def test_receive_no_stop_char(self):
        receiver = TCPReceiver()
        reader = FakeReader("GET|sensor1")

        result = await receiver.receive(reader)

        assert result is None

    @pytest.mark.asyncio
    async def test_receive_invalid_format_is_still_raw_string(self):
        receiver = TCPReceiver()
        reader = FakeReader("invalid$")

        result = await receiver.receive(reader)

        assert result == "invalid"

    @pytest.mark.asyncio
    async def test_receive_strips_whitespace(self):
        receiver = TCPReceiver()
        reader = FakeReader("  GET  |  sensor1  $")

        result = await receiver.receive(reader)

        assert result == "GET  |  sensor1"

    @pytest.mark.asyncio
    async def test_receive_multiple_chunks(self):
        receiver = TCPReceiver()

        class ChunkedReader:
            def __init__(self):
                self._chunks = [b"GET|sen", b"sor1$"]

            async def read(self, n):
                if not self._chunks:
                    return b""
                return self._chunks.pop(0)

        result = await receiver.receive(ChunkedReader())

        assert result == "GET|sensor1"

    def test_parse_request_get(self):
        receiver = TCPReceiver()

        result = receiver.parse_request("GET|sensor1")

        assert result.name == "get"
        assert result.request == GetRecordsRequest(name="sensor1")

    def test_parse_request_post(self):
        receiver = TCPReceiver()

        result = receiver.parse_request("POST|sensor1|25.5,sensor2|30.0")

        assert result.name == "post"
        assert result.request == PostRecordsRequest(records=[("sensor1", 25.5), ("sensor2", 30.0)])

    def test_parse_request_invalid(self):
        receiver = TCPReceiver()

        with pytest.raises(InvalidRequestError):
            receiver.parse_request("invalid")
