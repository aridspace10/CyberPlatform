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
        """Build an unprivileged identity from the client supplied session name.

        The current join flow has no trusted authentication context, so a client
        chosen username must never grant simulated administrative privileges.
        """
        name = username or "anonymous"
        if name == "root":
            name = "untrusted-root"
        group = "users"
        return cls(name, group, frozenset({group}), False)
