# MyJourney — backend

FastAPI-сервис (Python 3.14, async, Domain-Driven Design) — бэкенд монорепозитория MyJourney.

Общая документация лежит в корне репозитория:

- [README проекта](../README.md)
- [Архитектура](../docs/architecture.md)

## Локальная разработка

Бэкенд — самодостаточный uv-проект; все команды ниже запускаются из этой директории (`backend/`):

```bash
uv sync                 # установить зависимости в backend/.venv
uv run python -m app    # запустить приложение локально
make format             # ruff: автофиксы + формат
make lint               # ruff: lint
make typecheck          # ty: тайпчек
uv run pytest           # тесты (asyncio_mode=auto)
```

Полный стек (app + worker + postgres + frontend + логирование) поднимается из **корня** репозитория одной командой `make run`.
