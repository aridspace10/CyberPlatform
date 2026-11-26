"""Validated deployment overrides for session and diagnostic policies."""

import os
from collections.abc import Mapping
from dataclasses import dataclass


def _integer(
    environment: Mapping[str, str], name: str, default: int, minimum: int, maximum: int
) -> int:
    raw = environment.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{name} must be an integer from {minimum} to {maximum}"
        ) from error
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
    return value


@dataclass(frozen=True)
class SecuritySettings:
    session_creation_window_seconds: int
    session_creation_rate_limit: int
    active_session_limit: int
    log_retention_days: int
    max_log_file_bytes: int

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "SecuritySettings":
        environment = os.environ if environment is None else environment
        return cls(
            session_creation_window_seconds=_integer(
                environment,
                "CYBERPLATFORM_SESSION_CREATE_WINDOW_SECONDS",
                3600,
                60,
                86400,
            ),
            session_creation_rate_limit=_integer(
                environment, "CYBERPLATFORM_SESSION_CREATE_RATE_LIMIT", 20, 1, 100
            ),
            active_session_limit=_integer(
                environment, "CYBERPLATFORM_ACTIVE_SESSION_LIMIT", 10, 1, 50
            ),
            log_retention_days=_integer(
                environment, "CYBERPLATFORM_LOG_RETENTION_DAYS", 30, 1, 30
            ),
            max_log_file_bytes=_integer(
                environment, "CYBERPLATFORM_LOG_MAX_FILE_MIB", 5, 1, 5
            ) * 1024 * 1024,
        )


settings = SecuritySettings.from_environment()
