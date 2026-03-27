import pytest
from datetime import datetime
from domain.entities import Record


class TestRecord:
    def test_record_creation(self):
        record = Record(name="test", value=1.5, dttm=datetime.now())
        assert record.name == "test"
        assert record.value == 1.5

    def test_record_immutable(self):
        dttm = datetime.now()
        record = Record(name="test", value=1.5, dttm=dttm)
        with pytest.raises(AttributeError):
            record.name = "new"

    def test_record_equality(self):
        dttm = datetime(2024, 1, 1, 12, 0, 0)
        r1 = Record(name="test", value=1.5, dttm=dttm)
        r2 = Record(name="test", value=1.5, dttm=dttm)
        assert r1 == r2
