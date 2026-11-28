import datetime as dt
import json
from uuid import UUID

from app.shared.utils.json_serializer import serialize_to_json


def test_serialize_preserves_cyrillic_as_utf8() -> None:
    """Кириллица сериализуется как UTF-8, а не как ``\\uXXXX``-эскейпы."""
    result = serialize_to_json({"ключ": "значение"})

    assert json.loads(result) == {"ключ": "значение"}
    assert "значение" in result


def test_serialize_handles_uuid_and_datetime() -> None:
    """UUID → строка, datetime → ISO-строка (нативная поддержка orjson)."""
    identifier = UUID("12345678-1234-5678-1234-567812345678")
    moment = dt.datetime(2030, 1, 1, 12, 30, tzinfo=dt.UTC)

    parsed = json.loads(serialize_to_json({"id": identifier, "at": moment}))

    assert parsed["id"] == str(identifier)
    assert parsed["at"].startswith("2030-01-01T12:30")
