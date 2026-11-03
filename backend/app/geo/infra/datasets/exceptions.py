from collections.abc import Iterable

from app.geo.infra.datasets.manifest import DatasetSpec


class DatasetChecksumError(Exception):
    """Скачанный файл датасета не совпал с контрольной суммой из манифеста."""

    def __init__(self, *, spec: DatasetSpec, actual_sha256: str) -> None:
        super().__init__(
            f"Dataset {spec.name} {spec.version}: sha256 {actual_sha256} does not match manifest {spec.sha256}",
        )


class DatasetFormatError(Exception):
    """Файл датасета не соответствует формату из FORMAT.md."""


class DatasetColumnsError(DatasetFormatError):
    """Колонки файла не совпадают с форматом."""

    def __init__(self, *, columns: Iterable[str]) -> None:
        super().__init__(f"Unexpected dataset columns: {sorted(columns)}")


class UnknownVerdictCityError(Exception):
    """Вердикт арбитра ссылается на город, которого нет в датасете."""

    def __init__(self, *, external_id: str) -> None:
        super().__init__(f"Arbiter verdict references a city missing from the dataset: {external_id}")


class InvalidRuNameDecisionError(Exception):
    """Вердикт арбитра или строка файла решений не годится: пустое имя, неизвестный автор, повтор города."""

    def __init__(self, *, external_id: str, problem: str) -> None:
        super().__init__(f"Invalid ru name decision for {external_id}: {problem}")


class HumanDecisionOverrideError(Exception):
    """Вердикт арбитра пытается заменить решение, принятое человеком."""

    def __init__(self, *, external_id: str) -> None:
        super().__init__(f"Verdict for {external_id} would override a human decision; edit the decisions file instead")


class MissingEnglishNameError(DatasetFormatError):
    """У строки датасета нет имени на ``en`` — фолбэка отображения для любого языка."""

    def __init__(self, *, external_id: str) -> None:
        super().__init__(f"Dataset row {external_id} has no English name")


class MissingCountryCodeError(DatasetFormatError):
    """У строки датасета нет страны."""

    def __init__(self, *, external_id: str) -> None:
        super().__init__(f"Dataset row {external_id} has no country code")


class UnknownPlaceKindError(DatasetFormatError):
    """Тип места в датасете не из ``PlaceKindEnum``."""

    def __init__(self, *, external_id: str, kind: str) -> None:
        super().__init__(f"Dataset row {external_id} has unknown place kind {kind!r}")


class InvalidExternalIdError(DatasetFormatError):
    """Ключ строки датасета не вида ``<источник>:<ключ>``."""

    def __init__(self, *, external_id: str) -> None:
        super().__init__(f"Dataset row has invalid external_id {external_id!r}: expected <source>:<key>")


class InvalidCountryCodeError(DatasetFormatError):
    """Код страны в строке датасета — не ISO 3166-1 alpha-2."""

    def __init__(self, *, external_id: str, country_code: str) -> None:
        super().__init__(f"Dataset row {external_id} has invalid country code {country_code!r}")


class DuplicateCountryCodeError(DatasetFormatError):
    """Страна места в строке датасета указана дважды."""

    def __init__(self, *, external_id: str, country_code: str) -> None:
        super().__init__(f"Dataset row {external_id} lists country {country_code} twice")


class InvalidNumberError(DatasetFormatError):
    """Число в строке датасета не разбирается или вне допустимых пределов."""

    def __init__(self, *, external_id: str, column: str, value: str) -> None:
        super().__init__(f"Dataset row {external_id} has invalid {column} {value!r}")
