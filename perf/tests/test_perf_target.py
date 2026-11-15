import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import perf_target  # noqa: E402
import record_results  # noqa: E402


def test_a_path_becomes_an_absolute_sqlite_url(tmp_path):
    url = perf_target.to_url(str(tmp_path / "perf.db"))

    assert url == f"sqlite:///{tmp_path / 'perf.db'}"


def test_a_relative_path_becomes_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert perf_target.to_url("perf.db") == f"sqlite:///{tmp_path / 'perf.db'}"


def test_a_url_is_returned_unchanged():
    url = "postgresql://u:p@127.0.0.1:5432/registry_perf"

    assert perf_target.to_url(url) == url


@pytest.mark.parametrize("name", ["registry", "registry_test"])
def test_postgres_database_without_perf_in_its_name_is_refused(name):
    with pytest.raises(SystemExit):
        perf_target.check_rebuildable(f"postgresql://u:p@127.0.0.1:5432/{name}")


def test_postgres_database_with_perf_in_its_name_is_accepted():
    perf_target.check_rebuildable("postgresql://u:p@127.0.0.1:5432/registry_perf")


def test_sqlite_is_always_rebuildable():
    perf_target.check_rebuildable("sqlite:////tmp/anything.db")


def test_safe_hides_the_password():
    shown = perf_target.safe("postgresql://u:secret@127.0.0.1:5432/registry_perf")

    assert "secret" not in shown
    assert "registry_perf" in shown


def test_dataset_line_names_the_engine():
    line = record_results.dataset_line("postgresql")

    assert "postgresql" in line
    assert "10,000 plots" in line
