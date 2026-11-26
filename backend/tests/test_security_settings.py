"""Deployment settings fail fast on invalid overrides."""

import pytest
from services.security_settings import SecuritySettings


def test_security_settings_defaults_and_overrides():
    defaults = SecuritySettings.from_environment({})
    assert defaults.session_creation_window_seconds == 3600
    assert defaults.session_creation_rate_limit == 20
    assert defaults.active_session_limit == 10
    assert defaults.log_retention_days == 30
    assert defaults.max_log_file_bytes == 5 * 1024 * 1024

    configured = SecuritySettings.from_environment(
        {
            "CYBERPLATFORM_SESSION_CREATE_WINDOW_SECONDS": "1800",
            "CYBERPLATFORM_SESSION_CREATE_RATE_LIMIT": "12",
            "CYBERPLATFORM_ACTIVE_SESSION_LIMIT": "6",
            "CYBERPLATFORM_LOG_RETENTION_DAYS": "14",
            "CYBERPLATFORM_LOG_MAX_FILE_MIB": "2",
        }
    )
    assert configured.session_creation_window_seconds == 1800
    assert configured.session_creation_rate_limit == 12
    assert configured.active_session_limit == 6
    assert configured.log_retention_days == 14
    assert configured.max_log_file_bytes == 2 * 1024 * 1024


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CYBERPLATFORM_SESSION_CREATE_RATE_LIMIT", "0"),
        ("CYBERPLATFORM_ACTIVE_SESSION_LIMIT", "51"),
        ("CYBERPLATFORM_LOG_RETENTION_DAYS", "31"),
        ("CYBERPLATFORM_LOG_MAX_FILE_MIB", "not-a-number"),
    ],
)
def test_security_settings_reject_invalid_values(name, value):
    with pytest.raises(ValueError, match=name):
        SecuritySettings.from_environment({name: value})
