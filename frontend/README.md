# MyJourney — frontend

SPA на Vite + React 19 + TypeScript 7 + Mantine 9. Часть монорепо MyJourney; оркестрация
всего стека — из корня (`make run`), см. корневой `CLAUDE.md`.

## Требования

- **Node 26**, npm 11 — жёстко задано в `engines` и `.nvmrc`, CI гоняет ту же версию.
  На более старом Node `npm ci` упадёт с `EBADENGINE`. Это не баг, а гарантия того, что
  локальная сборка совпадает с CI.

## Команды

Все — из `frontend/`.

```bash
npm ci                # установка строго по lock-файлу (не npm install)
npm run dev           # Vite dev-сервер на :5173, /v1 проксируется на backend

make lint             # oxlint. ESLint в проекте НЕТ — мигрировали, конфига нет
make lint-fix         # oxlint --fix. Форматтера/prettier тоже нет
make typecheck        # tsc -b (нативный компилятор TS 7)
make test             # vitest: unit + component, один прогон
make test-unit        # только *.test.ts   — чистая логика
make test-component   # только *.test.tsx  — рендер React
make coverage         # то же + покрытие; порог 90%
make mantine-styles   # src/mantineStyles.ts = ровно те стили Mantine, что нужны используемым компонентам
make check            # lint + typecheck + mantine-styles + audit + test — ровно то, что гоняет CI
```

E2E — единственное, что запускается **из корня**, а не отсюда:

```bash
make test-e2e         # из КОРНЯ: поднимает одноразовый стек → Playwright → сносит с -v
make test-e2e-dev     # из КОРНЯ: по УЖЕ поднятому дев-стеку. Быстро (нет подъёма стека),
                      # но пишет в ДЕВ-базу. Сузить: E2E_ARGS="--project=chromium"
```

`frontend/Makefile` тоже имеет таргет `test-e2e`, но он лишь гоняет Playwright против уже
поднятого `E2E_BASE_URL` и стек не поднимает — обычно его дёргает корневой.

## Структура

```
src/
├── api/            # HTTP-клиент, доменные вызовы, маппинг ошибок (zod на границе)
├── auth/           # токены, jwt, контекст сессии, диалог верификации
├── components/     # переиспользуемое; globe/ — общая база 3D-глобуса
├── i18n/           # конфиг i18next, реестр языков
├── locales/<lang>/ # переводы по namespace (common, auth, errors, journeys, landing)
├── pages/          # экраны; публичная зона (лендинг, login, signup) под общим PublicLayout
├── test/           # общие сиды тестов: setup, render с провайдерами, MSW-хендлеры
├── index.css       # дизайн-токены (:root) — единственный источник значений
└── theme.ts        # тема Mantine поверх тех же токенов
e2e/                # Playwright-спеки по флоу
```

## Что стоит знать до первой правки

- **Стили — только через токены.** `index.css` держит два слоя: палитра (`--ink`, `--sun`) и
  семантика (`--surface`, `--text`, `--accent`). UI пользуется **только семантикой** — имя по
  цвету не подсказывает, куда его класть. Сырой hex или числовой кегль в компоненте — нарушение;
  проверяется скиллом `style-audit`.
- **Тесты лежат рядом с кодом**, а не в зеркальном дереве: `jwt.ts` → `jwt.test.ts`.
  Конвенции — в `.claude/rules/typescript/testing.md`.
- **Текст ошибки хранится i18n-токеном, а не готовой строкой.** Иначе сообщение застывает в
  языке, на котором его создали, и не переводится при переключении.
- **Тяжёлое грузится лениво.** three.js / react-globe.gl уезжает отдельным чанком — глобус не
  должен блокировать первую отрисовку. Проверять по графу СТАТИЧЕСКИХ импортов собранных
  чанков: динамический `import()` попадает в манифест предзагрузки и легко читается как
  статическая зависимость.
- Порог покрытия 90% форсится pre-commit хуком (`make hooks` из корня, разово), а не CI.
- **`node_modules` в дев-контейнере — отдельный docker-том**, он затеняет то, что лежит в образе.
  Контейнер на старте сам делает `npm install`, поэтому после правки `package.json` достаточно
  перезапустить фронт (из корня):
  `docker compose --project-directory . -f ops/docker-compose.base.yaml -f ops/docker-compose.yaml restart frontend`.
  Тот же перезапуск лечит «Что-то пошло не так» после `PARSE_ERROR` посреди правок — Vite продолжает
  отдавать сломанный модуль, и перезагрузка вкладки не помогает. Полный сброс тома —
  `... rm -sf frontend && docker volume rm myjourney_frontend_node_modules && make run`; не
  `down -v`: он снесёт и данные Postgres/Loki/Grafana.
- **`Cannot find module` из `node_modules/.bin/*`** — несвежая установка, лечится `npm ci`.
