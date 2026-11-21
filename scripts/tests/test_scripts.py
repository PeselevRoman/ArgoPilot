"""Tests for scripts/lib.sh (the shared helpers) and the checks in scripts/dev.sh.

Run from the repository root, with the registry's Python:
    services/registry-service/.venv/bin/python -m pytest scripts/tests
No real service is started: the helpers are called directly, with local sockets.
"""

import http.server
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
LIB = SCRIPTS / "lib.sh"


def bash(code: str, env: dict[str, str] | None = None, timeout: int = 30):
    """Run bash code with lib.sh loaded, and return the finished process."""
    return subprocess.run(
        ["bash", "-c", f'source "{LIB}"; {code}'],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
        timeout=timeout,
    )


@pytest.mark.parametrize("name", ["lib.sh", "dev.sh", "check.sh"])
def test_script_has_valid_syntax(name):
    assert subprocess.run(["bash", "-n", str(SCRIPTS / name)]).returncode == 0


@pytest.mark.parametrize("name", ["dev.sh", "check.sh"])
def test_script_is_executable(name):
    assert os.access(SCRIPTS / name, os.X_OK)


# --- port_in_use -------------------------------------------------------------


def test_port_in_use_is_true_for_a_listening_port_and_false_after_it_closes():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    port = server.getsockname()[1]
    assert bash(f"port_in_use {port}").returncode == 0
    server.close()
    assert bash(f"port_in_use {port}").returncode == 1


# --- wait_for_http -----------------------------------------------------------


class _Ok(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # keep the test output quiet
        pass


def test_wait_for_http_succeeds_when_the_url_answers():
    server = http.server.HTTPServer(("127.0.0.1", 0), _Ok)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        port = server.server_address[1]
        assert bash(f"wait_for_http http://127.0.0.1:{port}/ 10").returncode == 0
    finally:
        server.shutdown()


def test_wait_for_http_fails_after_the_timeout_when_nothing_answers():
    free = socket.socket()
    free.bind(("127.0.0.1", 0))
    port = free.getsockname()[1]
    free.close()
    started = time.monotonic()
    assert bash(f"wait_for_http http://127.0.0.1:{port}/ 2").returncode != 0
    assert time.monotonic() - started < 10


# --- load_user_env -----------------------------------------------------------


def test_load_user_env_exports_variables_from_the_file(tmp_path):
    env_file = tmp_path / "agropilot-env"
    env_file.write_text("TEST_DATABASE_URL=postgresql://u:p@localhost/registry_test\n")
    result = bash(
        'load_user_env; echo "$TEST_DATABASE_URL"',
        env={"AGROPILOT_ENV_FILE": str(env_file)},
    )
    assert result.stdout.strip() == "postgresql://u:p@localhost/registry_test"


def test_load_user_env_does_nothing_when_the_file_is_missing(tmp_path):
    result = bash(
        "load_user_env; echo done",
        env={"AGROPILOT_ENV_FILE": str(tmp_path / "missing")},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "done"


# --- require_test_db: the registry tests drop the five tables, so the name must say "test" ----


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@127.0.0.1:5432/registry_test",
        "postgresql://u:p@127.0.0.1:5432/registry_test?sslmode=require",
        "postgresql://u:p@localhost/test",
    ],
)
def test_require_test_db_accepts_a_database_named_test(url):
    assert bash(f'require_test_db "{url}"').returncode == 0


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@127.0.0.1:5432/registry",
        "postgresql://u:p@127.0.0.1:5432/registry_perf",
        "postgresql://test:test@127.0.0.1:5432/registry",  # "test" in the user, not the database
        "postgresql://u:p@127.0.0.1:5432/registry?options=test",  # "test" only in the query
    ],
)
def test_require_test_db_refuses_any_other_database(url):
    result = bash(f'require_test_db "{url}"')
    assert result.returncode == 1  # the helper's own refusal, not "command not found" (127)
    assert "registry_test" in result.stderr


def test_require_test_db_does_not_print_the_password():
    result = bash('require_test_db "postgresql://u:s3cret@127.0.0.1:5432/registry"')
    assert result.returncode == 1
    assert "s3cret" not in result.stdout + result.stderr


# --- run_suite and print_summary ----------------------------------------------


def test_summary_marks_passing_and_failing_suites_and_fails_overall(tmp_path):
    result = bash(
        'run_suite good . echo "3 passed in 0.1s"; run_suite bad . bash -c "echo 2 failed; exit 1"; print_summary',
        env={"LOG_DIR": str(tmp_path)},
    )
    assert result.returncode == 1
    assert "PASS" in result.stdout and "good" in result.stdout and "3 passed" in result.stdout
    assert "FAIL" in result.stdout and "bad" in result.stdout and "2 failed" in result.stdout
    assert (tmp_path / "check-bad.log").exists()


def test_summary_succeeds_when_every_suite_passes(tmp_path):
    result = bash('run_suite one . true; run_suite two . true; print_summary', env={"LOG_DIR": str(tmp_path)})
    assert result.returncode == 0


def test_a_passing_suite_that_prints_nothing_useful_says_ok(tmp_path):
    result = bash("run_suite quiet . true; print_summary", env={"LOG_DIR": str(tmp_path)})
    line = [l for l in result.stdout.splitlines() if "quiet" in l][0]
    assert line.split()[-1] == "ok"


def test_the_word_error_in_a_passing_suites_output_is_not_its_note(tmp_path):
    result = bash(
        'run_suite warn . bash -c "echo Warning: an error happened somewhere; exit 0"; print_summary',
        env={"LOG_DIR": str(tmp_path)},
    )
    line = [l for l in result.stdout.splitlines() if "warn" in l][0]
    assert line.split()[-1] == "ok"


def test_a_failing_suite_does_not_stop_the_next_one(tmp_path):
    result = bash('run_suite bad . false; run_suite after . true; print_summary', env={"LOG_DIR": str(tmp_path)})
    assert "after" in result.stdout


# --- dev.sh --check -----------------------------------------------------------


def test_dev_check_names_a_port_that_is_already_in_use():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    port = server.getsockname()[1]
    try:
        result = subprocess.run(
            [str(SCRIPTS / "dev.sh"), "--check"],
            capture_output=True,
            text=True,
            env={**os.environ, "DEV_PORTS": str(port)},
            timeout=30,
        )
    finally:
        server.close()
    assert result.returncode == 1
    assert str(port) in result.stdout + result.stderr
