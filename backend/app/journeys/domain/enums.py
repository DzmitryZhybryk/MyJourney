from enum import StrEnum


class TransportTypeEnum(StrEnum):
    """
    Среда передвижения в поездке (а не конкретный вид транспорта).

    Категория среды, не средство: пешком/машина/поезд = ``LAND``, самолёт = ``AIR``,
    паром/корабль = ``WATER``. Зеркалит string-literal union на фронте.
    """

    LAND = "land"
    AIR = "air"
    WATER = "water"
