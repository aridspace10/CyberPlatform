# Security policy settings

These optional environment variables are read when the backend starts. Unset
variables use the defaults below; invalid or out-of-range values stop startup
with a descriptive error. Restart the backend after changing a value.

| Variable | Default | Allowed range | Purpose |
| --- | ---: | ---: | --- |
| `CYBERPLATFORM_SESSION_CREATE_WINDOW_SECONDS` | 3600 | 60–86400 | Fixed window for each user's session creation quota |
| `CYBERPLATFORM_SESSION_CREATE_RATE_LIMIT` | 20 | 1–100 | Sessions a user may create in one window |
| `CYBERPLATFORM_ACTIVE_SESSION_LIMIT` | 10 | 1–50 | Waiting or running sessions a user may own |
| `CYBERPLATFORM_LOG_RETENTION_DAYS` | 30 | 1–30 | Age after which diagnostic records and idle session log directories are pruned |
| `CYBERPLATFORM_LOG_MAX_FILE_MIB` | 5 | 1–5 | Maximum size of each session diagnostic JSONL file in MiB |

These are deployment policy overrides. WebSocket message size limits, the
redaction marker, and log directory matching rules remain code constants.
Keep any deployment environment file outside the repository.
