# app-level config: swagger / redoc / openapi toggle and the JWT_SECRET startup check

import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import main


BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_docs_are_on_by_default():
    client = TestClient(main.app)
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_docs_flag_reads_env_values():
    assert main.api_docs_enabled(None) is True
    assert main.api_docs_enabled("true") is True
    assert main.api_docs_enabled("false") is False
    assert main.api_docs_enabled("FALSE") is False


def test_docs_off_hides_swagger_redoc_and_openapi():
    client = TestClient(FastAPI(**main.docs_urls(False)))
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_app_refuses_to_start_with_a_short_jwt_secret():
    # fresh interpreter so the module-level check runs again
    env = {**os.environ, "JWT_SECRET": "too-short"}
    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode != 0
    assert "JWT_SECRET" in result.stderr
