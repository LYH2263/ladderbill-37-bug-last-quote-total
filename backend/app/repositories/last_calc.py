import sqlite3

from app.repositories import runs as runs_repo


def save(
    conn: sqlite3.Connection,
    account_id: int,
    kwh: float,
    peak: bool,
    total: float,
    run_id: int,
    success_at: str | None = None,
) -> dict:
    """Persist the latest successful calc summary for an account (upsert)."""
    if not success_at:
        row = runs_repo.get(conn, run_id)
        success_at = row["created_at"]
    total = float(total)
    conn.execute(
        """
        INSERT INTO account_last_calc(account_id, kwh, peak, total, run_id, success_at)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(account_id) DO UPDATE SET
            kwh=excluded.kwh,
            peak=excluded.peak,
            total=excluded.total,
            run_id=excluded.run_id,
            success_at=excluded.success_at
        """,
        (account_id, kwh, 1 if peak else 0, total, run_id, success_at),
    )
    conn.commit()
    return {
        "account_id": account_id,
        "kwh": kwh,
        "peak": peak,
        "total": total,
        "run_id": run_id,
        "success_at": success_at,
    }


def get(conn: sqlite3.Connection, account_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM account_last_calc WHERE account_id=?", (account_id,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["peak"] = bool(d["peak"])
    return d


def delete(conn: sqlite3.Connection, account_id: int) -> bool:
    cur = conn.execute("DELETE FROM account_last_calc WHERE account_id=?", (account_id,))
    conn.commit()
    return cur.rowcount > 0
