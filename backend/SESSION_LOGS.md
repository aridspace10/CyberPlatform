# Session diagnostic logs

The WebSocket terminal writes two append-only JSON Lines files for each session:

- `activity.jsonl` records session connections and terminal input metadata,
  including the timestamp, user, input kind and length, outcome, status,
  interaction mode, and request correlation ID.
- `errors.jsonl` records unexpected exception types and stack frame locations
  with the same request correlation ID as the corresponding activity entry.

Expected command errors are recorded as activity outcomes. They do not go into the
error log. Log directories are named with a readable, sanitized session ID and a
hash suffix, so different session IDs cannot collide and path separators cannot
escape the log root.

By default, logs are written under `backend/logs/sessions/`. Set
`CYBERPLATFORM_LOG_DIR` to choose a different absolute directory. The directory is
created as needed and is ignored by Git. Each record is flushed after it is
written. If the log directory is unavailable, terminal handling continues and the
diagnostic record may be lost. On POSIX, session directories and log files are
restricted to the backend process owner (0700 and 0600). On Windows, restrict
the configured root with an appropriate NTFS ACL.

Terminal input is not stored verbatim. The `input` field is always `[redacted]`,
and the length is retained for diagnosis. Working directory and interaction
prompts are also redacted because they may contain filenames typed by users.
Exception messages and source lines are omitted because they can contain user
input. Authentication and join packets are not recorded. These records support
failure correlation but cannot replay a command; users should supply a
reproduction separately if needed.

In the session's **General** tab, a member can download a ZIP containing their
own activity and error records. The download endpoint requires the user's bearer
token and verifies their session membership; it filters both logs to that user's
ID so another player's commands and tracebacks are not included. Users can attach
the downloaded ZIP to a support report.

The default retention target is 30 days. Old records in active files are removed on
later writes or downloads, and each JSONL file is capped at 5 MiB. Inactive
session log directories older than 30 days are removed when a new session
logger starts; cleanup runs at most once daily per backend process. A dormant
deployment may retain old files until it next handles a session, so operators
should also schedule cleanup for strict retention requirements. Backups of the
log root need their own retention policy. Keep any logs needed to investigate
an active issue outside the automatic cleanup path.

The retention period and per-file size cap can be set through the validated
environment overrides in [Security policy settings](SECURITY_SETTINGS.md).

For a hosted frontend, set `VITE_BACKEND_URL` at build time to the backend's
public HTTP(S) origin. Set `CYBERPLATFORM_CORS_ORIGINS` on the backend to a
comma-separated list of the frontend origins that may call it. The defaults keep
local development on `http://localhost:5173` and `http://localhost:8000`.

Set `CYBERPLATFORM_JWT_SECRET` to the same long, random value on every backend
worker. When unset, the backend generates a different secret each time it
starts. This is convenient for local development, but it signs users out after
every restart and cannot support multiple workers. Keep the configured secret
outside the repository and rotate it if it is disclosed.
