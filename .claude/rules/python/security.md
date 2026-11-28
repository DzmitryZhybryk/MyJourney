---
paths:
  - "backend/**/*.py"
---
# Python security

Extends `common/security.md`.

- Secrets and config come only from the settings module (pydantic-settings, frozen, cached). No
  `os.environ[...]` / `load_dotenv()` in app code — it bypasses validation and `frozen=True`.
- A sensitive field is `SecretStr` (an API key, a signing secret), so it cannot leak through
  `repr()` or a structured logger; unwrap with `.get_secret_value()` only where the value is used.
- Security lint is ruff's `S` rules (flake8-bandit) inside the normal lint run, never a separate
  bandit; dependency CVEs have their own audit target.
