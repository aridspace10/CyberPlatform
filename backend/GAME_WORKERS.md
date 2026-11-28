# Game worker deployment

Live lobbies, connected sockets, generated questions, chat, scoring, and host
actions use the in-memory `SessionManager`. Deploy exactly **one backend worker
and one backend instance**. Keep all HTTP and WebSocket traffic on that instance.
Do not set Uvicorn or Gunicorn worker counts above one, and do not autoscale the
backend horizontally.

Startup holds an operating-system lock for the full ASGI lifespan. By default,
the lock file is next to the SQLite database (`app.runtime.lock`). A second
process using the same database path fails startup rather than serving a
different game state. `WEB_CONCURRENCY` and `UVICORN_WORKERS` must equal `1` if
set. A process crash releases the lock automatically; the small lock file can
remain on disk.

When configuring a different datastore, set `CYBERPLATFORM_RUNTIME_LOCK_FILE`
to a stable path on storage shared by all processes on that host. A local file
lock does not coordinate separate hosts or containers with separate filesystems.
The deployment must therefore run one instance until shared game coordination
is implemented. Scale the frontend independently if needed.
