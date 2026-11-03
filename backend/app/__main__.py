import uvicorn

from app.shared.settings import settings


def run_application() -> None:
    """
    Запускает API под uvicorn с хостом, портом и reload из настроек.

    Scenarios:
        - локальный запуск API без Docker
    """
    uvicorn.run(
        "app.main:create_app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        factory=True,
    )


if __name__ == "__main__":
    run_application()
