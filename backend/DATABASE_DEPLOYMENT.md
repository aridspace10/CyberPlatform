# Persistent database deployment

The backend currently supports SQLite and a **single backend worker**. Mount a
persistent volume at a directory outside the source checkout, for example
`/var/lib/cyberplatform`. Set these environment variables on the backend service:

```text
CYBERPLATFORM_ENV=production
CYBERPLATFORM_DATABASE_PATH=/var/lib/cyberplatform/app.db
```

The mount directory must exist and be writable by the backend process. Startup
fails if the production path is missing, relative, or unwritable. Do not use an
ephemeral filesystem for this path. The application upgrades existing SQLite
tables at startup with idempotent schema changes; `db.session.upgrade_schema`
is the upgrade entry point. Back up the volume before deploying schema changes.
Local development uses `backend/app.db` by default, independent of the current
working directory, and this file is ignored by Git.

## First deployment and redeployment

1. Start with an empty volume. Do not copy a checkout's `backend/app.db` or a
   development backup to the production volume. The committed development DB
   was removed from the current tree but remains in Git history.
2. From `backend/`, start the application using the configured environment.
   Startup creates the schema and seeds only public scenarios. It does not
   create a user unless the local development quick-login flag is enabled.
3. Create a public test account and Sandbox through the API/UI. Redeploy with
   the same mounted volume and database path. Verify that account, its Sandbox,
   and its saved shell still exist. Redeploying with a new empty volume loses
   those records.

## Backup and restore

From `backend/`, with the same database environment variables as the service:

```sh
python -m db.maintenance backup /secure/backups/cyberplatform-YYYYMMDD.db
```

The backup uses SQLite's online backup API, runs an integrity check, and writes
the destination atomically. Protect and retain backups according to the host's
data policy. Practice restoring to an isolated path before relying on them:

```sh
CYBERPLATFORM_DATABASE_PATH=/tmp/cyberplatform-restore.db \
  python -m db.maintenance restore /secure/backups/cyberplatform-YYYYMMDD.db
```

For production recovery, stop **all** backend workers, preserve the damaged
database, and restore to the configured production path with `--force`. Start
one worker and verify the test account and Sandbox. Keep the previous DB until
the restored service has been checked. Do not use `--force` against a live DB.

## Development records in Git history

Removing `backend/app.db` from the current tree does not erase old commits or
copies. Before public launch, review who had access to that history, retire
development accounts/passwords that appeared in the old DB, and rotate any
reused secrets. Provisioning the deployment JWT signing secret is tracked by
CYB-46. The hosting volume, backup schedule, and live restore drill must be
verified in the deployment environment; this repository cannot provision them.
