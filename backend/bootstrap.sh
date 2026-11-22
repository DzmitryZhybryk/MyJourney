#!/bin/sh
# Подготовка базы перед стартом app и worker: идемпотентные шаги по порядку, первый упавший
# останавливает остальные. Новый шаг — строка `step` внизу.
set -eu

# Та же форма JSON, что у structlog в app.shared.logging: Alloy берёт level, logger и timestamp.
# Подставляются только константы скрипта, поэтому без экранирования.
log() {
  level=$1 event=$2 name=$3 extra=${4:-}
  printf '{"event":"%s","level":"%s","logger":"bootstrap","step":"%s"%s,"timestamp":"%s"}\n' \
    "$event" "$level" "$name" "$extra" "$(date -u +%Y-%m-%dT%H:%M:%S.%6NZ)"
}

step() {
  name=$1
  shift
  log info bootstrap.step_started "$name"
  started_ms=$(date +%s%3N)
  status=0
  "$@" || status=$?
  duration=",\"duration_ms\":$(($(date +%s%3N) - started_ms))"
  if [ "$status" -ne 0 ]; then
    log error bootstrap.step_failed "$name" "$duration,\"exit_code\":$status"
    exit "$status"
  fi
  log info bootstrap.step_finished "$name" "$duration"
}

step alembic_upgrade alembic upgrade head
step procrastinate_schema python -m app.shared.infra.procrastinate
step media_config_seed python -m app.media.scripts.seed_config
