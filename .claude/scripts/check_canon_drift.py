"""Fail when a rule adopted from the personal canon has drifted from it.

A file under `.claude/rules/` whose path also exists under `~/.claude/optional/rules/` is a copy of
that canon file plus a `paths:` frontmatter; stripped of the frontmatter the two must match. The
canon lives only on the owner's machine, so without it the check passes. Run from the repo root:
`make canon-drift`.
"""

import re
import sys
from pathlib import Path

CANON_ROOT = Path.home() / ".claude" / "optional" / "rules"
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def body(path: Path) -> str:
    return FRONTMATTER.sub("", path.read_text(), count=1).lstrip("\n")


def report(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def main() -> int:
    if not CANON_ROOT.is_dir():
        report(f"  canon not found at {CANON_ROOT}, nothing to compare")
        return 0

    project_root = Path.cwd() / ".claude" / "rules"
    adopted = tuple(
        (canon, project_root / canon.relative_to(CANON_ROOT))
        for canon in sorted(CANON_ROOT.rglob("*.md"))
        if (project_root / canon.relative_to(CANON_ROOT)).is_file()
    )
    drifted = tuple((canon, copy) for canon, copy in adopted if body(copy) != body(canon))

    report(f"  {len(adopted)} rules adopted from the canon, {len(drifted)} drifted")
    for canon, copy in drifted:
        report(f"      {copy.relative_to(Path.cwd())}: diff {canon} {copy}")

    if drifted:
        report("Re-copy the canon into the project (keep the `paths:` frontmatter), or change the canon first.")

    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
