"""Unit-тесты ``great_circle_km`` — расстояние по большой окружности между двумя точками."""

import pytest

from app.shared.utils.great_circle import great_circle_km


def test_great_circle_km_moscow_to_london() -> None:
    """Москва → Лондон ≈ 2500 км."""
    distance_km = great_circle_km(
        origin_latitude=55.75,
        origin_longitude=37.62,
        destination_latitude=51.5,
        destination_longitude=-0.12,
    )

    assert distance_km == pytest.approx(2500, abs=60)


def test_great_circle_km_one_degree_of_latitude() -> None:
    """1° широты по тому же меридиану ≈ 111 км (опорная проверка haversine)."""
    distance_km = great_circle_km(
        origin_latitude=0.0,
        origin_longitude=0.0,
        destination_latitude=1.0,
        destination_longitude=0.0,
    )

    assert distance_km == pytest.approx(111.2, abs=0.5)


def test_great_circle_km_same_coordinates_is_zero() -> None:
    """Одинаковые координаты — расстояние 0."""
    distance_km = great_circle_km(
        origin_latitude=39.8,
        origin_longitude=-89.6,
        destination_latitude=39.8,
        destination_longitude=-89.6,
    )

    assert distance_km == 0
