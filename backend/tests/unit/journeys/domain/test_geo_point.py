"""Unit-тесты value object ``GeoPoint`` — расстояние маршрута."""

import pytest

from tests.builders import LONDON_CITY_ID, make_geo_point


def test_distance_km_to_moscow_to_london_is_great_circle_distance() -> None:
    """distance_km_to: Москва → Лондон по большой окружности ≈ 2500 км."""
    moscow = make_geo_point()
    london = make_geo_point(city_id=LONDON_CITY_ID, country_code="GB", latitude=51.5, longitude=-0.12)

    assert moscow.distance_km_to(destination=london) == pytest.approx(2500, abs=60)


def test_distance_km_to_same_point_is_zero() -> None:
    """distance_km_to: до той же точки — 0 км."""
    moscow = make_geo_point()

    assert moscow.distance_km_to(destination=moscow) == 0
