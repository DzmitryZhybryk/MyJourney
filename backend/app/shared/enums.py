from enum import StrEnum


class AppEnvEnum(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class SortDirectionEnum(StrEnum):
    ASC = "asc"
    DESC = "desc"
