"""Offline SQLite backup and restore commands for a persistent deployment."""

import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from .configuration import database_path


def copy_database(source, destination, *, replace=False):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if source == destination:
        raise ValueError("Source and destination database paths must differ")
    if not source.is_file():
        raise FileNotFoundError(f"Source database does not exist: {source}")
    if destination.exists() and not replace:
        raise FileExistsError(f"Destination already exists: {destination}")
    if not destination.parent.is_dir():
        raise FileNotFoundError(
            f"Destination directory does not exist: {destination.parent}"
        )

    # sqlite3.backup captures a consistent snapshot even if the source uses WAL.
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as old:
            with closing(sqlite3.connect(temporary)) as new:
                if old.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError(
                        f"Source database failed integrity check: {source}"
                    )
                old.backup(new)
                if new.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Copied database failed integrity check")
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup", help="Snapshot the configured database")
    backup.add_argument("destination", type=Path)
    restore = commands.add_parser(
        "restore", help="Restore while the backend is stopped"
    )
    restore.add_argument("source", type=Path)
    restore.add_argument(
        "--force", action="store_true", help="Replace an existing database"
    )
    args = parser.parse_args(argv)
    target = database_path()
    if args.command == "backup":
        copy_database(target, args.destination)
    else:
        copy_database(args.source, target, replace=args.force)


if __name__ == "__main__":
    main()
