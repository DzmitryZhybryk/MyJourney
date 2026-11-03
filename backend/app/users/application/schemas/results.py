from dataclasses import dataclass

__all__ = ["CurrentUserResult"]


@dataclass(frozen=True, slots=True)
class CurrentUserResult:
    display_name: str
