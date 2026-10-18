from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EffectiveIdentity:
    """The simulated user and group used for filesystem permission checks."""

    username: str = "user"
    primary_group: str = "user"
    groups: frozenset[str] = field(default_factory=lambda: frozenset({"user"}))
    privileged: bool = False

    @classmethod
    def for_session(cls, username: str, user_id: str = "") -> EffectiveIdentity:
        """Build a session identity; only the explicit root identity is privileged."""
        name = username or "anonymous"
        is_root = name == "root"
        group = "root" if is_root else "users"
        return cls(name, group, frozenset({group}), is_root)
