#!/bin/sh
# Админ одноразового e2e-стека: регистрация обычным API, роль — боевым скриптом первого админа, так e2e
# проходят тот же путь, что и настоящий админ. Учётные данные повторяет frontend/e2e/helpers/admin.ts.
set -eu

username=e2e_admin
email=e2e-admin@example.com
password=e2e-Admin-Password-1

python -m devtools.e2e_admin --api-url http://app:8000 --username "$username" --email "$email" --password "$password"
python -m app.auth.scripts.set_admin_role --email "$email"
