from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parent.parent / "deploy" / "aws"
UNIT = DEPLOY / "career-platform.service"
NGINX = DEPLOY / "nginx-career-platform.conf"
DEPLOY_SH = DEPLOY / "deploy.sh"


def _exec_start() -> str:
    return next(l for l in UNIT.read_text().splitlines() if l.startswith("ExecStart="))


def test_service_binds_loopback_only():
    # Nginx is the only thing that should reach Uvicorn. Uvicorn's
    # X-Forwarded-Proto trust (FORWARDED_ALLOW_IPS) defaults to 127.0.0.1.
    assert "--host 127.0.0.1" in _exec_start()
    assert "0.0.0.0" not in _exec_start()


def test_service_runs_unprivileged_from_the_app_root():
    unit = UNIT.read_text()
    assert "User=ubuntu" in unit
    # app/main.py mounts "app/static" and "app/templates" by relative path.
    assert "WorkingDirectory=/home/ubuntu/career-platform" in unit
    assert "ExecStart=/home/ubuntu/career-platform/.venv/bin/uvicorn app.main:app" in unit


def test_service_restarts_and_starts_at_boot():
    unit = UNIT.read_text()
    assert "Restart=on-failure" in unit
    assert "WantedBy=multi-user.target" in unit


def test_nginx_proxies_to_the_port_the_service_listens_on():
    port = re.search(r"--port (\d+)", _exec_start()).group(1)
    assert f"proxy_pass http://127.0.0.1:{port};" in NGINX.read_text()


def test_nginx_answers_for_the_test_name_and_the_domain():
    conf = NGINX.read_text()
    assert "server_name aws.dhwanijain.me dhwanijain.me;" in conf


def test_nginx_forwards_host_and_scheme():
    conf = NGINX.read_text()
    assert "proxy_set_header Host $host;" in conf
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in conf
    assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in conf


def test_deploy_script_applies_schema_before_restart():
    s = DEPLOY_SH.read_text()
    assert s.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in s
    assert s.index("uv sync --frozen --no-dev") < s.index("-m scripts.init_db") < s.index(
        "systemctl restart career-platform"
    )


def test_deploy_script_never_seeds():
    # The guide: seeding on AWS could overwrite or unpublish the restored data.
    s = DEPLOY_SH.read_text()
    assert "seed" not in s
    assert "copy_sqlite_to_postgres" not in s


def test_deploy_script_requires_the_database_backed_page():
    # /health never touches the database; / returns 503 when it is down.
    s = DEPLOY_SH.read_text()
    assert "http://127.0.0.1:8000/health" in s
    assert "http://127.0.0.1:8000/" in s.replace("http://127.0.0.1:8000/health", "")


def test_deploy_script_is_executable():
    assert os.access(DEPLOY_SH, os.X_OK)


@pytest.mark.parametrize("path", [UNIT, NGINX, DEPLOY_SH], ids=lambda p: p.name)
def test_no_secrets_in_deploy_files(path):
    text = path.read_text()
    assert not re.search(r"postgres(?:ql)?://[^\s/:@]+:[^\s/@]+@", text), "credentialed URL"
    assert "rds.amazonaws.com" not in text, "RDS endpoint belongs in .env, not git"
