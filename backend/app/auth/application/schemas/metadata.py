from dataclasses import dataclass

__all__ = ["ClientMetadata"]


@dataclass(frozen=True, slots=True)
class ClientMetadata:
    ip_address: str | None = None
    user_agent: str | None = None
