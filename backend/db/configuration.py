"""Database location and startup checks for local and hosted deployments."""

import os
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = BACKEND_DIR / "app.db"


def database_path(environ=None):
    """Resolve a SQLite file without depending on the process working directory."""
    environ = os.environ if environ is None else environ
    production = environ.get("CYBERPLATFORM_ENV", "development").lower() == "production"
    configured = environ.get("CYBERPLATFORM_DATABASE_PATH", "").strip()
    if production and not configured:
        raise RuntimeError(
            "CYBERPLATFORM_DATABASE_PATH must name a persistent SQLite file "
            "in production"
        )
    path = Path(configured).expanduser() if configured else DEFAULT_DATABASE
    if not path.is_absolute():
        raise RuntimeError("CYBERPLATFORM_DATABASE_PATH must be an absolute path")
    path = path.resolve()
    if production and path.is_relative_to(BACKEND_DIR.parent.resolve()):
        raise RuntimeError("Production database must be outside the source checkout")
    return path


def check_database_storage(path):
    """Fail before startup when the configured volume cannot store a database."""
    parent = path.parent
    if not parent.is_dir():
        raise RuntimeError(f"Database directory does not exist: {parent}")
    if path.exists() and (not path.is_file() or not os.access(path, os.W_OK)):
        raise RuntimeError(f"Database file is not writable: {path}")
    try:
        with tempfile.TemporaryFile(dir=parent):
            pass
    except OSError as exc:
        raise RuntimeError(f"Database directory is not writable: {parent}") from exc


def database_url(path):
    return f"sqlite:///{path.as_posix()}"
