import pytest

from tests.builders import LONDON_POINT, MOSCOW_POINT


def test_distance_km_to_moscow_to_london_is_great_circle_distance() -> None:
    """Москва → Лондон по большой окружности ≈ 2500 км."""
    assert MOSCOW_POINT.distance_km_to(LONDON_POINT) == pytest.approx(2500, abs=60)
