# Session diagnostic logs

The WebSocket terminal writes two append-only JSON Lines files for each session:

- `activity.jsonl` records session connections and terminal inputs, including the
  timestamp, user, command or foreground response, working directory, outcome,
  status, interaction prompt, and request correlation ID.
- `errors.jsonl` records unexpected exceptions with their traceback and the same
  request correlation ID as the corresponding activity entry.

Expected command errors are recorded as activity outcomes. They do not go into the
error log. Log directories are named with a readable, sanitized session ID and a
hash suffix, so different session IDs cannot collide and path separators cannot
escape the log root.

By default, logs are written under `backend/logs/sessions/`. Set
`CYBERPLATFORM_LOG_DIR` to choose a different absolute directory. The directory is
created as needed and is ignored by Git. Each record is flushed after it is
written. If the log directory is unavailable, terminal handling continues and the
diagnostic record may be lost.

Terminal input is stored verbatim so a failure can be replayed. This can include
private data typed into a command or interactive prompt. Restrict access to the log
directory like access to session data, and avoid typing credentials into commands.
Authentication and join packets are not recorded. Exception messages and
tracebacks may include values from command input.

Logs remain on disk across disconnects and server restarts. They currently have no
automatic expiry; operators should archive or remove session directories older
than their chosen retention period. A 30-day retention period is a reasonable
starting point for a development deployment. Keep any logs needed to investigate
an active issue before pruning them.
