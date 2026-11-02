# Логи

## Откуда берутся

Каждый контейнер пишет логи в stdout. Бэкенд (API, воркер, CLI-шаги) пишет **одну JSON-строку на запись** — и
свои строки, и строки библиотек (uvicorn, procrastinate).

```
контейнеры myjourney* ──stdout──▶ Alloy (ops/alloy-config.alloy) ──▶ Loki (ops/loki.yaml, 7 дней) ──▶ Grafana
```

- **Alloy** читает логи через Docker API, только у контейнеров с `myjourney` в имени, и помнит позицию чтения в
  томе `alloy_data`. Из JSON-строки он достаёт `level` и `logger` в метки, а `timestamp` — во время строки.
- **Grafana** подключает Loki сама (`ops/grafana/provisioning/datasources/loki.yaml`), руками ничего настраивать не
  нужно. Дев: `http://localhost:${GRAFANA_PORT:-3000}`; прод — по SSH-туннелю (`docs/deployment.md`, раздел 8).
  Логин и пароль — `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` из `.env`.

## Метки (по ним Loki ищет быстро)

| Метка | Значение |
|---|---|
| `app` | всегда `myjourney` |
| `container` | имя контейнера: `myjourney_app`, `myjourney_worker`, … |
| `stream` | `stdout` или `stderr` |
| `level` | `debug`, `info`, `warning`, `error`, `critical` — только у JSON-строк |
| `logger` | имя логгера: `app.shared.logging.middleware`, `procrastinate.worker`, `uvicorn.error`, … |

## Поля строки

Есть всегда: `event` (имя события), `level`, `logger`, `timestamp`.

Внутри HTTP-запроса API к любой строке добавляются:

- `trace_id` — номер запроса: по нему находятся все строки одного запроса;
- `span_id` — этап запроса, на котором написана строка;
- `user_id` — если запрос авторизован.

**Строка запроса** (`event="http.request"`, одна на каждый HTTP-запрос): `method`, `path`, `route` (шаблон пути,
например `/v1/journeys/{journey_id}`), `status_code`, `process_time` (секунды), `client_ip`, `query_params`. Если
запрос закончился ошибкой — ещё `error_type`, `error_code` (код, ушедший клиенту) и `error_message`; у ошибки
уровня `error` есть `exception` с трейсбеком. Текст ошибки валидации (422) не пишется: в нём сырой ввод клиента.

Уровень строки запроса: наш сбой (500, необработанное исключение) — `error` с трейсбеком; ошибка клиента (4xx) —
`warning`; остальное — `info`.

**Имена событий** — `<домен или вертикаль>.<что случилось>`: `geo.city_ids_unknown`, `http_client.timeout`,
`component.startup_failed`, `api.started`. Строки библиотек сохраняют собственный текст в `event`, кроме
procrastinate: у него событие — `procrastinate.<действие>` (`start_job`, `job_success`, `job_error`,
`jobs_deferred`, …), а аргументы задач из строки убраны — среди них бывают секреты. Id задачи, имя, очередь и
длительность остаются в полях `job` и `jobs`.

## Частые запросы (LogQL, Grafana → Explore → Loki)

```logql
# Все строки одного запроса
{app="myjourney"} | json | trace_id="e051fadea4d9e0c466de59cca022cbfd"

# Ошибки бэкенда
{container="myjourney_app", level="error"}

# Запросы с ошибкой сервера и их тип
{container="myjourney_app"} | json | event="http.request" and status_code >= 500

# Медленные запросы
{container="myjourney_app"} | json | event="http.request" and process_time > 1

# Запросы к одному эндпоинту
{container="myjourney_app"} | json | route="/v1/journeys/{journey_id}"

# Всё, что делал пользователь
{app="myjourney"} | json | user_id="<uuid>"

# Фоновые задачи
{container="myjourney_worker", logger="procrastinate.worker"}

# Упавшие фоновые задачи
{container="myjourney_worker"} | json | event=~"procrastinate.job_error.*"
```

## Без Grafana

В деве Loki открыт на порту 3100:

```bash
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={container="myjourney_app", level="error"}' \
  --data-urlencode "start=$(($(date +%s) - 3600))000000000" \
  --data-urlencode 'limit=50' | jq -r '.data.result[]?.values[]?[1]'
```

Последние строки одного контейнера без Loki: `docker logs --tail 50 myjourney_app`.
