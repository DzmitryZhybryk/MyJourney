"""Unit-тесты чтения манифеста датасетов."""

from pathlib import Path

import pytest

from app.geo.infra.datasets.manifest import DatasetFormatEnum, DatasetSpec, read_manifest


def test_read_manifest_returns_datasets_in_declared_order(tmp_path: Path) -> None:
    """read_manifest: каждая секция [[dataset]] → DatasetSpec, порядок как в файле."""
    manifest_path = tmp_path / "manifest.toml"
    manifest_path.write_text(
        """
[[dataset]]
name = "cities"
format = "cities"
version = "v1"
url = "https://example.test/cities.csv.gz"
sha256 = "aaa"

[[dataset]]
name = "lakes"
format = "places"
version = "v2"
url = "https://example.test/lakes.csv.gz"
sha256 = "bbb"
""",
        encoding="utf-8",
    )

    datasets = read_manifest(path=manifest_path)

    assert datasets == (
        DatasetSpec(
            name="cities",
            format=DatasetFormatEnum.CITIES,
            version="v1",
            url="https://example.test/cities.csv.gz",
            sha256="aaa",
        ),
        DatasetSpec(
            name="lakes",
            format=DatasetFormatEnum.PLACES,
            version="v2",
            url="https://example.test/lakes.csv.gz",
            sha256="bbb",
        ),
    )


@pytest.mark.parametrize(
    ("format_line", "error"),
    [("", KeyError), ('format = "rivers"', ValueError)],
    ids=["missing-format", "unknown-format"],
)
def test_read_manifest_rejects_dataset_without_known_format(
    tmp_path: Path,
    format_line: str,
    error: type[Exception],
) -> None:
    """read_manifest: без format или с форматом не из DatasetFormatEnum манифест не читается."""
    manifest_path = tmp_path / "manifest.toml"
    manifest_path.write_text(
        f"""
[[dataset]]
name = "rivers"
{format_line}
version = "v1"
url = "https://example.test/rivers.csv.gz"
sha256 = "aaa"
""",
        encoding="utf-8",
    )

    with pytest.raises(error):
        read_manifest(path=manifest_path)


def test_read_manifest_default_path_reads_shipped_manifest() -> None:
    """read_manifest: манифест из репозитория читается и описывает хотя бы один датасет."""
    datasets = read_manifest()

    assert len(datasets) > 0
    assert all(len(dataset.sha256) == 64 for dataset in datasets)
