"""Verify a local PostgreSQL backup into a NEW database; no existing DB is replaced or deleted."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import psycopg
from psycopg import sql

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

if not settings.DEBUG or not settings.DEMO_MODE:
    raise SystemExit("Backup verification helper requires explicit local DEBUG + DEMO_MODE.")
cfg = settings.DATABASES["default"]
if cfg["ENGINE"] != "django.db.backends.postgresql" or cfg.get("HOST") not in {"127.0.0.1", "localhost"}:
    raise SystemExit("This helper is limited to loopback PostgreSQL.")
execution_root = root
if os.name == "nt" and not str(root).isascii():
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest().upper()[:12]
    junction = Path(tempfile.gettempdir()) / f"smart-sales-pg-{digest}"
    if not junction.exists() or junction.resolve() != root.resolve():
        raise SystemExit("Run scripts/local_postgres.ps1 start first to prepare the verified ASCII junction.")
    execution_root = junction
bin_root = execution_root / ".tools" / "pgsql" / "bin"
suffix = ".exe" if os.name == "nt" else ""
dump_tool, restore_tool = bin_root / f"pg_dump{suffix}", bin_root / f"pg_restore{suffix}"
if not dump_tool.exists() or not restore_tool.exists():
    raise SystemExit("Portable PostgreSQL tools are not installed. Follow README backup commands instead.")
backup_root = execution_root / ".local" / "backups"
backup_root.mkdir(parents=True, exist_ok=True)
identifier = uuid.uuid4().hex[:10]
restore_name = f"smart_sales_restore_{identifier}"
dump_path = backup_root / f"smart-sales-{identifier}.dump"
environment = dict(os.environ, PGHOST=cfg.get("HOST") or "127.0.0.1", PGPORT=str(cfg.get("PORT") or 5432), PGUSER=cfg["USER"], PGPASSWORD=cfg["PASSWORD"], PGDATABASE=cfg["NAME"])
subprocess.run([str(dump_tool), "-Fc", "--file", str(dump_path)], env=environment, check=True)
connect = {"host": environment["PGHOST"], "port": environment["PGPORT"], "user": cfg["USER"], "password": cfg["PASSWORD"]}
with psycopg.connect(**connect, dbname="postgres", autocommit=True) as admin:
    admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(restore_name)))
subprocess.run([str(restore_tool), "--no-owner", "--no-privileges", "--dbname", restore_name, str(dump_path)], env=environment, check=True)
counts = {}
with psycopg.connect(**connect, dbname=cfg["NAME"]) as original, psycopg.connect(**connect, dbname=restore_name) as restored:
    for table in ("accounts_user", "catalog_product", "customers_customer", "orders_salesorder", "orders_salesorderitem", "payments_payment", "inventory_stockbalance", "inventory_inventorymovement", "core_auditlog"):
        query = sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
        before = original.execute(query).fetchone()[0]
        after = restored.execute(query).fetchone()[0]
        if before != after:
            raise SystemExit(f"Backup verification failed for table {table}.")
        counts[table] = after
record = {"status": "pass", "restore_database": restore_name, "backup_file": str(dump_path.relative_to(execution_root)), "counts": counts, "preserved": "Original and verification databases both retained; no data deleted."}
(root / ".local" / "backup-verification.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
