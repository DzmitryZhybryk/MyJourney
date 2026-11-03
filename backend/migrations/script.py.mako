"""
Migration name: ${message}

Revision ID: ${up_revision}
Revises: ${down_revision if down_revision else "None"}
Create Date: ${create_date}
"""
# pylint: disable=no-member,invalid-name

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports + "\n" if imports else ""}<%
def clean_code(code):
    """Удаляет комментарии Alembic, исправляет отступы и заменяет одинарные кавычки на двойные."""
    if not code:
        return "pass"

    lines = [line for line in code.split("\n") if "# ###" not in line and "# end Alembic" not in line]
    if not lines:
        return "pass"

    # Находим минимальный отступ и обрабатываем строки за один проход
    min_indent = min((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
    cleaned_lines = []
    in_args = False

    for i, line in enumerate(lines):
        if not line.strip():
            cleaned_lines.append("")
            continue

        # Удаляем минимальный отступ и заменяем кавычки
        cleaned = (line[min_indent:] if min_indent > 0 and line.startswith(" " * min_indent) else line).replace("'", '"')

        # Определяем аргументы функции по предыдущей строке
        prev_line = lines[i-1].strip() if i > 0 else ""
        if prev_line.endswith(("(", ",")):
            in_args = True

        # Добавляем отступ для аргументов
        if in_args:
            cleaned_lines.append("        " + cleaned.lstrip())
            if cleaned.strip().endswith(")"):
                in_args = False
        else:
            # Первую строку отступает сам шаблон, остальные операторы тела — здесь.
            cleaned_lines.append("    " + cleaned if cleaned_lines else cleaned)

    # Удаляем пустые строки в конце
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)
%>
revision: str = "${up_revision}"
down_revision: str | None = ${'"' + str(down_revision) + '"' if down_revision else "None"}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels).replace("'", '"') if branch_labels else "None"}
depends_on: str | Sequence[str] | None = ${repr(depends_on).replace("'", '"') if depends_on else "None"}


def upgrade() -> None:
    ${clean_code(upgrades) if upgrades else "pass"}


def downgrade() -> None:
    ${clean_code(downgrades) if downgrades else "pass"}
