import json

import pytest

from app import seed
from app.db import connect
from app.services.billing_service import BillingService


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    monkeypatch.setattr("app.db.DB_PATH", tmp_path / "test.db")
    seed.init_db()
    with BillingService() as service:
        yield service


def test_successful_bill_persists_summary(svc):
    out = svc.run_bill(220, False, account_id=1, persist=True)
    summary = svc.get_last_calc(1)
    assert summary is not None
    assert summary["kwh"] == 220
    assert summary["peak"] is False
    # Card amount must equal the amount stored on the run in history
    assert summary["total"] == out["total"]
    assert summary["run_id"] == out["run_id"]
    run = svc.get_run(out["run_id"])
    assert summary["total"] == json.loads(run["result_json"])["total"]
    assert summary["success_at"] == run["created_at"]


def test_summary_total_is_amount_not_kwh(svc):
    out = svc.run_bill(400, True, account_id=1, persist=True)
    summary = svc.get_last_calc(1)
    assert summary["kwh"] == 400
    assert summary["total"] == out["total"] == 309.6
    assert summary["total"] != summary["kwh"]


def test_latest_success_overwrites_previous(svc):
    svc.run_bill(120, False, account_id=1, persist=True)
    second = svc.run_bill(400, True, account_id=1, persist=True)
    summary = svc.get_last_calc(1)
    assert summary["kwh"] == 400
    assert summary["peak"] is True
    assert summary["total"] == second["total"]
    assert summary["run_id"] == second["run_id"]
    run = svc.get_run(second["run_id"])
    assert summary["success_at"] == run["created_at"]


def test_repair_backfills_total_from_run(svc, tmp_path, monkeypatch):
    out = svc.run_bill(400, True, account_id=1, persist=True)
    # Simulate the old bug: total column holds the input kwh.
    conn = connect()
    conn.execute("UPDATE account_last_calc SET total=400 WHERE account_id=1")
    conn.commit()
    seed._repair_last_calc_totals(conn)
    fixed = conn.execute(
        "SELECT total, success_at FROM account_last_calc WHERE account_id=1"
    ).fetchone()
    conn.close()
    assert fixed["total"] == out["total"]
    run = svc.get_run(out["run_id"])
    assert fixed["success_at"] == run["created_at"]



def test_failed_calc_does_not_overwrite_summary(svc):
    svc.run_bill(120, False, account_id=1, persist=True)
    before = svc.get_last_calc(1)
    with pytest.raises(ValueError):
        svc.run_bill(-5, False, account_id=1, persist=True)
    after = svc.get_last_calc(1)
    assert after == before


def test_non_persisted_bill_does_not_write_summary(svc):
    svc.run_bill(220, False, account_id=1, persist=False)
    assert svc.get_last_calc(1) is None


def test_summary_without_account_not_saved(svc):
    svc.run_bill(220, False, account_id=None, persist=True)
    conn = connect()
    rows = conn.execute("SELECT COUNT(*) c FROM account_last_calc").fetchone()["c"]
    conn.close()
    assert rows == 0


def test_clear_last_calc(svc):
    svc.run_bill(120, False, account_id=1, persist=True)
    assert svc.clear_last_calc(1) is True
    assert svc.get_last_calc(1) is None
    # clearing again is a no-op, not an error
    assert svc.clear_last_calc(1) is False


def test_missing_summary_reads_none(svc):
    assert svc.get_last_calc(999) is None
