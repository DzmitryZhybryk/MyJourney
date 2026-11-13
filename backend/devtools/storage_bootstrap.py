"""
Настройка бакетов локального S3-эмулятора: оба бакета media, CORS на приватном, анонимное чтение публичного.

Только для dev, e2e и integration-тестов. Бакеты на проде настраиваются вручную, и этот модуль — описание
того, какими они должны быть. Запуск: ``python -m devtools.storage_bootstrap --cors-origin <origin фронта>``.
"""

import argparse
import asyncio
import json
from collections.abc import Sequence
from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

from app.media.infra.s3_client import open_s3_client
from app.shared.settings import settings

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


async def bootstrap_buckets(
    *,
    client: S3Client,
    private_bucket: str,
    public_bucket: str,
    cors_allowed_origins: Sequence[str],
) -> None:
    """
    Создаёт недостающие бакеты и заново применяет их настройки; повторный запуск ничего не ломает.

    Args:
        client: Клиент хранилища с правами на настройку бакетов
        private_bucket: Бакет, куда браузер кладёт оригиналы по подписанной ссылке
        public_bucket: Бакет готовых вариантов, читаемый анонимно
        cors_allowed_origins: Origin'ы фронта, которым разрешён PUT в приватный бакет
    """
    for bucket in (private_bucket, public_bucket):
        await _create_bucket_if_missing(client=client, bucket=bucket)

    await client.put_bucket_cors(
        Bucket=private_bucket,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedMethods": ["PUT"],
                    "AllowedOrigins": list(cors_allowed_origins),
                    "AllowedHeaders": ["*"],
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3600,
                },
            ],
        },
    )
    await client.put_bucket_policy(
        Bucket=public_bucket,
        Policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{public_bucket}/*"],
                    },
                ],
            },
        ),
    )


async def _create_bucket_if_missing(*, client: S3Client, bucket: str) -> None:
    try:
        await client.create_bucket(Bucket=bucket)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "BucketAlreadyOwnedByYou":
            raise


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Настройка бакетов локального S3-эмулятора")
    parser.add_argument("--cors-origin", action="append", required=True, dest="cors_origins")
    arguments = parser.parse_args()

    async with open_s3_client(settings) as client:
        await bootstrap_buckets(
            client=client,
            private_bucket=settings.MEDIA_S3_PRIVATE_BUCKET,
            public_bucket=settings.MEDIA_S3_PUBLIC_BUCKET,
            cors_allowed_origins=arguments.cors_origins,
        )


if __name__ == "__main__":
    asyncio.run(_main())
