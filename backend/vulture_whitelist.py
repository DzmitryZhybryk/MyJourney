"""
Whitelist для vulture: имена, используемые неявно и не видимые статическому анализу.

Сюда добавляются ТОЛЬКО honest false positives -- имена, которые читает фреймворк,
протокол или сериализатор, но vulture их не видит. Реальный мёртвый код в whitelist
добавлять не нужно: смысл vulture в том, чтобы он его подсвечивал.

Любое упоминание имени здесь делает его "использованным" с точки зрения vulture.
Декораторы (FastAPI-роуты, Pydantic-валидаторы) уже покрыты ignore_decorators
в pyproject.toml -- сюда они не попадают.
"""


class _Whitelist:
    pass


_ = _Whitelist()

# uvicorn --factory: точка входа, ищется по имени из shell-команды.
_.create_app

# Pydantic Settings / BaseModel: атрибуты, читаемые библиотекой через метаклассы.
_.model_config
_.Config
_.json_schema_extra

# Pydantic-поля схем: используются при сериализации в JSON-ответах.
_.token_type
# Курсор страницы: заполняется конструктором, наружу уходит сериализацией ответа.
_.next_cursor
# Карта перемещений: годы шкалы заполняются конструктором, наружу уходят сериализацией ответа.
_.first_year
_.last_year
# MovePlacement: значение приходит из тела запроса, сервис ветвится по AFTER, BEFORE — ветка else.
_.BEFORE

# AsyncContextManager (BaseUnitOfWork.__aexit__):
# имена параметров -- часть протокола, фреймворк передаёт их позиционно.
_.exc_val
_.exc_tb

# Starlette BaseHTTPMiddleware: вызывается фреймворком по имени метода.
_.dispatch

# request.state -- динамические атрибуты, ставятся в одном месте, читаются в другом
# (фильтр uvicorn-логгера).
_.exception_handled
_.exception_type

# Enum-варианты, выбираемые из значений .env / БД во время выполнения.
_.PRODUCTION
_.PREMIUM
_.ADMIN

# Приватные атрибуты, читаемые внутри методов того же класса
# (vulture не всегда отслеживает self.* через цепочку вызовов).
_._model

# geo_dataset_loads, geo_places: загрузчик работает с таблицами сырым SQL, ORM-модели нужны только метадате.
_.GeoDatasetLoad
_.loaded_at
_.kind
_.country_codes
_.notability

# TransportType: варианты выбираются из значений тела запроса/БД во время выполнения.
_.LAND
_.AIR
_.WATER

# DTO карты путешествий: поле читает pydantic через from_attributes при сборке ответа.
_.cities

# ВРЕМЕННО, не false positive: порт хранилища media появился раньше потока загрузки, который его вызывает.
# Удалить вместе с появлением вызывающего.
_.sign_upload
