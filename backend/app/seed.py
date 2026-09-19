import json

from app.db import connect
from app.engines.peak_compare import compare_plain_vs_peak
from app.engines.tier_progressive import calc_bill


def init_db():
    conn = connect()
    conn.executescript(
        """
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS accounts(
        id INTEGER PRIMARY KEY, name TEXT, meter_no TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY, account_id INTEGER, kwh REAL, peak INTEGER);
    CREATE TABLE IF NOT EXISTS tiers(id INTEGER PRIMARY KEY, up_to REAL, price REAL, sort_order INTEGER);
    CREATE TABLE IF NOT EXISTS calc_runs(
        id INTEGER PRIMARY KEY,
        kind TEXT,
        account_id INTEGER,
        input_json TEXT,
        result_json TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS account_last_calc(
        account_id INTEGER PRIMARY KEY,
        kwh REAL,
        peak INTEGER,
        total REAL,
        run_id INTEGER,
        success_at TEXT
    );
    """
    )
    if conn.execute("SELECT COUNT(*) c FROM accounts").fetchone()["c"] == 0:
        conn.execute(
            "INSERT INTO accounts(name, meter_no, note) VALUES ('张家', 'M-1001', '对照：正常用量')"
        )
        conn.execute(
            "INSERT INTO accounts(name, meter_no, note) VALUES ('李家(种子偏高)', 'M-1002', '对照：高用量+尖峰')"
        )
        conn.executemany(
            "INSERT INTO tiers(up_to, price, sort_order) VALUES (?,?,?)",
            [(180, 0.52, 1), (260, 0.62, 2), (None, 0.82, 3)],
        )
        conn.execute("INSERT INTO readings(account_id, kwh, peak) VALUES (1, 120, 0)")
        conn.execute("INSERT INTO readings(account_id, kwh, peak) VALUES (2, 400, 1)")
        conn.execute("INSERT INTO settings(key, value) VALUES ('peak_factor', '1.2')")
        conn.execute("INSERT INTO settings(key, value) VALUES ('currency', 'CNY')")
        tiers = [{"up_to": r[0], "price": r[1]} for r in [(180, 0.52), (260, 0.62), (None, 0.82)]]
        bill1 = calc_bill(120, tiers, 1.0)
        conn.execute(
            "INSERT INTO calc_runs(kind, account_id, input_json, result_json, created_at) VALUES (?,?,?,?,datetime('now'))",
            ("bill", 1, json.dumps({"kwh": 120, "peak": False}), json.dumps(bill1, ensure_ascii=False)),
        )
        cmp2 = compare_plain_vs_peak(400, tiers, 1.2)
        conn.execute(
            "INSERT INTO calc_runs(kind, account_id, input_json, result_json, created_at) VALUES (?,?,?,?,datetime('now'))",
            ("compare", 2, json.dumps({"kwh": 400}), json.dumps(cmp2, ensure_ascii=False)),
        )
        conn.commit()
    _repair_last_calc_totals(conn)
    conn.close()


def _repair_last_calc_totals(conn):
    """Backfill account_last_calc.total from the authoritative calc_runs row.

    Earlier builds stored the input kwh in the total column by mistake, so the
    summary card's amount did not match the run shown in history. Re-derive
    every stored total (and timestamp) from the referenced run.
    """
    rows = conn.execute(
        """
        SELECT lc.account_id, lc.run_id,
               r.result_json, r.created_at
        FROM account_last_calc lc
        JOIN calc_runs r ON r.id = lc.run_id
        """
    ).fetchall()
    for row in rows:
        result = json.loads(row["result_json"])
        total = result.get("total")
        if total is None:
            continue
        # Always rewrite: also normalizes older ISO-format success_at values.
        conn.execute(
            "UPDATE account_last_calc SET total=?, success_at=? WHERE account_id=?",
            (float(total), row["created_at"], row["account_id"]),
        )
    conn.commit()
