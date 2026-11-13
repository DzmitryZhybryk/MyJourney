# Деплой MyJourney на VPS

Прод-выкатка через docker compose + Caddy (авто-HTTPS) + GitHub Actions (CI/CD).
Все команды на сервере — из корня склонированного репозитория (compose-файлы живут в `ops/`,
запускаются через `make prod-*`).

## Архитектура прода

```
Интернет ──443/80──▶ Caddy (TLS, reverse-proxy) ─┬─ /v1/*  ▶ app:8000  (FastAPI)
                                                  └─ /*     ▶ frontend:8080 (nginx + SPA)
                     app/worker ▶ myjourney_pg (Postgres, НЕ виден снаружи)
                     myjourney_pg_backup ▶ pg_dump по расписанию
                     loki/alloy/grafana — логирование (наружу не публикуется)
```

- **Наружу открыт только Caddy** (80/443). Postgres/Grafana/Loki/app/frontend — без проброса портов,
  доступны лишь внутри docker-сети `myjourney-network`.
- Образы `myjourney-backend`/`myjourney-frontend` собирает CI и пушит в **GHCR**; сервер их только `pull`-ит.
- Миграции БД прогоняет one-shot `myjourney_migrate` (`alembic upgrade head` + схема procrastinate) до старта app/worker.
- Газеттир загружает one-shot `myjourney_geo_load` (`python -m app.geo.scripts.load_datasets`) после миграций и до старта app: скачивает датасеты из `manifest.toml` (GitHub Release), проверяет sha256 и пропускает уже загруженные версии.

## Предпосылки

- **VPS** (рекомендуется тариф от 6 GB RAM: postgres + app + worker + frontend + loki + alloy + grafana + caddy).
- **Домен** с возможностью править DNS.
- Аккаунт **Resend** для отправки email (верификация домена-отправителя).

---

## 1. Подготовка сервера

### 1.1. Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"   # разлогиниться/залогиниться для применения группы
```

### 1.2. Глобальный лимит логов Docker (предохранитель от переполнения диска)

Дублирует per-service лимиты из compose на уровне демона — на случай контейнеров без явного `logging`.
Создай `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
```

```bash
sudo systemctl restart docker
```

### 1.3. Firewall (ufw)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp     # SSH (укажи свой порт, если не 22)
sudo ufw allow 80/tcp     # HTTP (ACME + редирект на HTTPS)
sudo ufw allow 443/tcp    # HTTPS
sudo ufw allow 443/udp    # HTTP/3
sudo ufw enable
```

> ⚠️ Docker управляет iptables в обход ufw: если пробросить порт через `ports:`, он станет доступен
> извне **мимо** ufw. Поэтому в `ops/docker-compose.prod.yaml` внутренние сервисы намеренно без
> `ports:` — наружу торчит только Caddy. Не добавляй `ports:` postgres/grafana на проде.

### 1.4. Docker-сеть

```bash
docker network create myjourney-network
```

### 1.5. Клонирование репозитория и секреты

```bash
git clone git@github.com:DzmitryZhybryk/MyJourney.git /opt/myjourney
cd /opt/myjourney
cp .env.example .env
```

Заполни `.env` **новыми** прод-секретами (не переиспользуй dev-значения):

```bash
# сгенерировать секреты
openssl rand -hex 32      # -> JWT_SECRET_KEY
openssl rand -base64 32 | tr '+/' '-_'   # -> CHALLENGE_CODE_ENCRYPTION_KEY
openssl rand -base64 32   # -> POSTGRES_PASSWORD, GRAFANA_ADMIN_PASSWORD
```

Обязательно проставь: `ENVIRONMENT=production`, `RELOAD=` (пусто), `POSTGRES_ECHO=false`,
`POSTGRES_HOST=myjourney_pg`, `DOMAIN=<твой домен>`, `ACME_EMAIL=<email>`, `RESEND_*`.

### 1.6. Доступ к приватным образам GHCR

По умолчанию GHCR-пакеты приватные. На сервере нужно залогиниться, чтобы `pull` работал:

```bash
# PAT с правом read:packages (github.com → Settings → Developer settings → Tokens)
echo "$GHCR_PAT" | docker login ghcr.io -u <github-username> --password-stdin
```

Альтернатива — сделать пакеты `myjourney-backend`/`myjourney-frontend` публичными в настройках GHCR
(тогда `docker login` на сервере не нужен).

---

## 2. DNS и TLS

Пропиши **A-запись** домена на IP VPS **до первого старта Caddy** — Caddy берёт сертификат
Let's Encrypt по ACME HTTP-01, для чего домен уже должен резолвиться на сервер, а порты 80/443 быть
доступны из интернета.

```
A   @   <IP VPS>
```

Проверка: `dig +short <домен>` должен вернуть IP сервера.

> Для отладки прод-стека без реального домена задай в `.env` `DOMAIN=localhost` — Caddy выдаст
> самоподписанный внутренний сертификат.

---

## 3. Resend (email)

Отправка писем (верификация email) требует верифицированного домена-отправителя:

1. В Resend добавь домен и пропиши выданные **SPF/DKIM** DNS-записи.
2. В `.env`: `RESEND_FROM_EMAIL=no-reply@<твой-домен>`, `RESEND_API_KEY=<ключ>`.

---

## 4. GitHub Secrets (для автодеплоя)

`Settings → Secrets and variables → Actions` в репозитории:

| Secret | Значение |
|---|---|
| `SSH_HOST` | IP/хост VPS |
| `SSH_USER` | пользователь SSH на сервере |
| `SSH_KEY` | приватный SSH-ключ для деплоя (пару сгенерируй `ssh-keygen`, публичный — в `~/.ssh/authorized_keys` на сервере) |
| `SSH_PORT` | порт SSH (например `22`) |
| `DEPLOY_PATH` | путь к репо на сервере (например `/opt/myjourney`) |

`GITHUB_TOKEN` для пуша образов в GHCR выдаётся автоматически (`packages: write` в workflow).

### CI-гейты и запрет мержа при красных тестах

Тесты гоняют два воркфлоу по стратегии git-flow (feature → dev → main): `ci.yml` — быстрый гейт,
`prod.yml` — тяжёлый гейт + сборка образов + деплой. На PR → `dev` `prod.yml` не запускается вовсе,
поэтому там нет skipped-чеков:

| Событие | Workflow | Job'ы | Что проверяется |
|---|---|---|---|
| PR → `dev` | `ci.yml` | `Backend gate`, `Frontend gate` | быстрые: lint, typecheck, arch, unit, api, component |
| PR → `main` | `ci.yml` + `prod.yml` | + `Backend integration`, `E2E (Playwright)` | + integration (testcontainers) + e2e |
| push → `main` | `ci.yml` + `prod.yml` | всё + `Build & push` + `Deploy` | полный гейт → сборка образов → деплой |

Чтобы **красные тесты блокировали мерж**, включи branch protection (нужны admin-права на репо):
`GitHub → Settings → Branches → Add branch ruleset` для `dev` и `main`:

- ✅ **Require a pull request before merging** (запрет прямого push);
- ✅ **Require status checks to pass** → добавь для `dev`: `Backend gate`, `Frontend gate`;
  для `main` — ещё `Backend integration`, `E2E (Playwright)`;
- ✅ **Require branches to be up to date before merging** (перегон гейта после rebase).

> Без этой настройки CI лишь *показывает* статус, но не мешает мержить красное — branch protection
> на `dev`/`main` обязателен. На push в `main` деплой жёстко связан с тяжёлыми тестами внутри
> `prod.yml`: `build-push` объявлен через `needs: [backend-integration, e2e]`, а `deploy` — через
> `needs: build-push`, поэтому **красные integration/e2e блокируют сборку образов и деплой**. Быстрый
> гейт (`Backend`/`Frontend gate`) живёт в `ci.yml` и гейтит деплой не через `needs`, а через
> Required status checks (branch protection не даёт смержить красный PR в `main`).

---

## 5. Первый деплой

```bash
cd /opt/myjourney
make prod-pull    # стянуть образы из GHCR
make prod-up      # поднять стек (миграции прогонятся автоматически до app)
```

Проверка:

```bash
make prod-config                              # раскрытый прод-конфиг
docker compose --project-directory . -f ops/docker-compose.base.yaml -f ops/docker-compose.prod.yaml ps
curl -I https://<домен>/                      # должен ответить 200/301 через Caddy
```

Первый админ: зарегистрируйтесь через сайт, затем на сервере

```bash
make prod-set-admin-role email=<email>
```

Скрипт работает только пока админа нет; дальше роли меняются из админки. Новая роль попадёт в токен при
следующем входе или обновлении сессии (откройте сайт в новой вкладке).

Дальнейшие деплои идут **автоматически**: push/merge в `main` → `prod.yml` прогоняет тяжёлый гейт →
при зелёных тестах job'ы `build-push` (образы в GHCR) и `deploy` (SSH: `git pull && make prod-pull &&
make prod-up`) выкатывают прод. Красные тесты → деплой не запускается.

Ручной деплой (без CI): `make prod-pull && make prod-up` на сервере.

---

## 6. Миграции

- Прогоняются автоматически one-shot сервисом `myjourney_migrate` — `app`/`worker`
  стартуют только после его успешного завершения (`service_completed_successfully`). Он делает два шага:
  `alembic upgrade head` (таблицы приложения) и `python -m app.shared.infra.procrastinate` (таблицы очереди
  задач). Без второй схемы не работает ни worker, ни регистрация в app: она кладёт письмо в очередь.
- Схема procrastinate применяется, только если её ещё нет в базе: версию команда не сверяет. При обновлении
  procrastinate проверь `procrastinate/sql/migrations/` в установленном пакете — файлы новее прежней версии
  нужно применить к базе вручную до деплоя новой версии.
- Если миграция упала — app не поднимется (это защита: не запускаем код на несовместимой схеме).
  Смотри логи: `docker compose ... logs myjourney_migrate`.
- **Перед деплоем с рискованной миграцией сделай бэкап** (см. ниже).
- После миграций one-shot `myjourney_geo_load` загружает газеттир; app тоже ждёт его успешного
  завершения. Повторный деплой без смены `manifest.toml` ничего не скачивает. Новая версия датасета =
  новый ассет в GitHub Release + новые version/url/sha256 в `backend/app/geo/infra/datasets/manifest.toml`.
  Упал — смотри `docker compose ... logs myjourney_geo_load` (нет сети до GitHub, не сошёлся sha256, битый файл).

---

## 7. Бэкапы и восстановление

Сервис `myjourney_pg_backup` (`prodrigestivill/postgres-backup-local`) делает `pg_dump` по расписанию
(`@daily`) с ротацией (7 дней / 4 недели / 6 месяцев) в volume `myjourney_pg_backups`.

```bash
# посмотреть дампы
docker run --rm -v myjourney_pg_backups:/backups alpine ls -lah /backups/daily

# ручной бэкап прямо сейчас
docker exec myjourney_pg_backup /backup.sh
```

**Восстановление** из дампа:

```bash
# найти нужный дамп в /backups/{daily,weekly,monthly}, затем:
docker exec -i myjourney_pg sh -c \
  'gunzip | psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backup.sql.gz
```

> ⚠️ Дампы лежат на диске сервера — это защита от логической порчи, **не от гибели диска**.
> Для durability: (1) тарифные снапшоты сервера (evps «Backups: Included»), (2) периодически
> копируй `myjourney_pg_backups` во внешнее хранилище (S3/rclone) отдельным cron.
> `pg_data` и `myjourney_pg_backups` НЕ удаляй командой `down -v` — потеряешь данные.

---

## 8. Логи и мониторинг

- **Loki** хранит логи 7 дней (`ops/loki.yaml`, `retention_period: 168h`).
- **Alloy** собирает логи контейнеров `myjourney*` через Docker API (`ops/alloy-config.alloy`) и помнит позицию
  чтения в томе `alloy_data`. Первый запуск один раз перечитывает историю контейнеров — дубли в Loki за это
  окно ожидаемы. Устаревший контейнер `myjourney_promtail` удаляет `make prod-up` (`--remove-orphans`).
- Docker json-file логи ограничены `10m × 3` на контейнер (compose + `daemon.json`).
- **Grafana** наружу не публикуется; источник данных Loki подключается сам
  (`ops/grafana/provisioning/datasources/`). Доступ админа — по SSH-туннелю:

  ```bash
  ssh -L 3000:localhost:3000 <user>@<VPS>
  # затем http://localhost:3000 (логин/пароль из GRAFANA_ADMIN_*)
  ```

---

## 9. Troubleshooting и откат

- **Caddy не берёт сертификат** — проверь, что DNS указывает на сервер (`dig +short <домен>`) и
  порты 80/443 открыты (ufw + провайдер). Логи: `docker compose ... logs caddy`.
- **app unhealthy** — `docker compose ... logs app`; проверь `.env` (POSTGRES_HOST=myjourney_pg, секреты).
- **Откат на предыдущую версию** — образы тегируются commit-SHA. На сервере:

  ```bash
  IMAGE_TAG=<предыдущий-sha> make prod-pull
  IMAGE_TAG=<предыдущий-sha> make prod-up
  ```

- **Автодеплой упал на `git pull --ff-only`** — на сервере правили tracked-файл руками (например,
  `ops/Caddyfile`). Перед мержем в `main`: `git restore <файл>` на сервере. Сменился только конфиг
  Caddy — `make prod-up` контейнер не пересоздаст, нужен `docker compose ... restart caddy`.
- **Полная остановка** (данные сохраняются): `make prod-down`.
