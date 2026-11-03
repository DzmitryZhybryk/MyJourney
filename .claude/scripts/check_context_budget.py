"""Fail when the Claude instructions loaded for an area of work outgrow their budget.

Counts only what lives in this repo. `CLAUDE.md`, rules without `paths:` and skill descriptions
load at session start; a rule with `paths:` joins the first time Claude touches a matching file
and stays for the rest of the session. Run from the repo root: `make context-budget`.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# Any file of the area works as the sample: rules are matched against it by their `paths:` globs.
AREAS: dict[str, tuple[str | None, int]] = {
    "session start": (None, 20_500),
    "backend app": ("backend/app/journeys/application/services/journey.py", 56_500),
    "backend shared": ("backend/app/shared/infra/di/registry.py", 59_200),
    "backend tests": ("backend/tests/unit/journeys/application/test_journey_service.py", 33_000),
    "frontend src": ("frontend/src/pages/journeys/JourneyForm.tsx", 31_000),
    "frontend tests": ("frontend/src/pages/journeys/JourneyForm.test.tsx", 42_000),
}
FRONTMATTER_PATHS = re.compile(r'\A---\npaths:\n((?:  - "[^"]+"\n)+)---\n')
SKILL_DESCRIPTION = re.compile(r"^description:.*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class Rule:
    name: str
    size: int
    globs: tuple[str, ...]


def read_globs(text: str) -> tuple[str, ...]:
    match = FRONTMATTER_PATHS.match(text)
    return tuple(re.findall(r'"([^"]+)"', match.group(1))) if match else ()


def load_rules(root: Path) -> tuple[Rule, ...]:
    return tuple(
        Rule(name=str(path.relative_to(root)), size=path.stat().st_size, globs=read_globs(path.read_text()))
        for path in sorted(root.glob(".claude/rules/**/*.md"))
    )


def session_start_files(*, root: Path, rules: tuple[Rule, ...]) -> dict[str, int]:
    descriptions = {
        f"{path.relative_to(root)} (description)": len(SKILL_DESCRIPTION.search(path.read_text()).group().encode())
        for path in sorted(root.glob(".claude/skills/*/SKILL.md"))
    }
    always_on_rules = {rule.name: rule.size for rule in rules if not rule.globs}
    return {"CLAUDE.md": (root / "CLAUDE.md").stat().st_size} | always_on_rules | descriptions


def matching_rules(*, sample: str, rules: tuple[Rule, ...]) -> dict[str, int]:
    path = PurePosixPath(sample)
    return {rule.name: rule.size for rule in rules if any(path.full_match(glob) for glob in rule.globs)}


def report(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def main() -> int:
    root = Path.cwd()
    rules = load_rules(root)
    start = session_start_files(root=root, rules=rules)
    is_failed = False

    for area, (sample, budget) in AREAS.items():
        matched = {} if sample is None else matching_rules(sample=sample, rules=rules)
        if sample is not None and not matched:
            report(f"  {area}: no rule matches {sample} — the sample or the frontmatter parsing is broken")
            is_failed = True
            continue

        files = start | matched
        total = sum(files.values())
        report(f"  {area:<15} {total:>7,} / {budget:,} B")
        if total > budget:
            is_failed = True
            for name, size in sorted(files.items(), key=lambda item: -item[1]):
                report(f"      {size:>7,}  {name}")

    if is_failed:
        report("Over budget: trim the largest files above, or raise the budget in AREAS if the growth is deliberate.")

    return 1 if is_failed else 0


if __name__ == "__main__":
    sys.exit(main())
