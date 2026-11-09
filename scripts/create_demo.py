"""Create an ignored random local demo password, then safely run idempotent seed."""
import os
import secrets
import sys
from pathlib import Path

project = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402

if not settings.DEBUG or not settings.DEMO_MODE:
    raise SystemExit("This helper is limited to explicit local DEBUG + DEMO_MODE environments.")
password_file = project / ".local" / "demo-password.txt"
password_file.parent.mkdir(parents=True, exist_ok=True)
if not password_file.exists():
    password_file.write_text(secrets.token_urlsafe(24) + "-Ss9!", encoding="utf-8")
os.environ["SMART_SALES_DEMO_PASSWORD"] = password_file.read_text(encoding="utf-8").strip()
call_command("seed_demo", password_env="SMART_SALES_DEMO_PASSWORD")
print("Local demo password remains in .local/demo-password.txt (ignored by Git).")
