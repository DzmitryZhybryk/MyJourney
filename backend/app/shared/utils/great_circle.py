import math

# Средний радиус Земли в километрах для great-circle оценки расстояния.
EARTH_RADIUS_KM = 6371.0


def great_circle_km(
    *,
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> int:
    """
    Считает расстояние по большой окружности (haversine) между двумя точками, км.

    Сферическая оценка по средней модели Земли (без эллипсоидности) — для схематичной карты
    этого достаточно.

    Scenarios:
        - расстояние маршрута по координатам его концов

    Args:
        origin_latitude: Широта первой точки
        origin_longitude: Долгота первой точки
        destination_latitude: Широта второй точки
        destination_longitude: Долгота второй точки

    Returns:
        Расстояние в километрах, округлённое до ближайшего целого
    """
    start_phi = math.radians(origin_latitude)
    end_phi = math.radians(destination_latitude)
    delta_phi = math.radians(destination_latitude - origin_latitude)
    delta_lambda = math.radians(destination_longitude - origin_longitude)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(start_phi) * math.cos(end_phi) * math.sin(delta_lambda / 2) ** 2
    return round(2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a)))
