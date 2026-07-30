"""
Persistence for the creator rewards points program.

Design choice: points are stored as a ledger (every award/deduction is its
own row), not a single mutable balance column. A balance is just SUM(amount)
for a user. This makes the full history free to query, makes bugs
self-correcting (nothing to get out of sync), and makes refunds trivial
(insert a reversing row instead of mutating state).
"""

import os
import sqlite3
import threading

DB_PATH = os.path.join("data", "rewards.db")
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS points_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                points INTEGER NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS challenge_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                note TEXT,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rewards_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                cost INTEGER NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS redemption_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reward_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                cost INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                fulfilled_by INTEGER,
                fulfilled_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()


# ---- settings ----

def get_setting(key: str, default=None):
    with _lock, _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


def get_log_channel_id():
    val = get_setting("log_channel_id")
    return int(val) if val else None


# ---- points ledger ----

def add_points(user_id: int, amount: int, reason: str, created_by: int = None) -> int:
    """amount can be negative (deduction, redemption spend, refund reversal, etc)."""
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO points_ledger (user_id, amount, reason, created_by) VALUES (?, ?, ?, ?)",
            (user_id, amount, reason, created_by),
        )
        conn.commit()
        return cur.lastrowid


def get_balance(user_id: int) -> int:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM points_ledger WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row["total"]


def get_history(user_id: int, limit: int = 10) -> list[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM points_ledger WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_leaderboard(limit: int = 10) -> list[tuple]:
    with _lock, _connect() as conn:
        rows = conn.execute("""
            SELECT user_id, SUM(amount) AS total FROM points_ledger
            GROUP BY user_id
            HAVING total > 0
            ORDER BY total DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [(r["user_id"], r["total"]) for r in rows]


# ---- challenges ----

def add_challenge(name: str, description: str, points: int) -> int:
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO challenges (name, description, points) VALUES (?, ?, ?)",
            (name, description, points),
        )
        conn.commit()
        return cur.lastrowid


def get_active_challenges() -> list[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM challenges WHERE active = 1 ORDER BY points DESC").fetchall()
        return [dict(r) for r in rows]


def get_challenge(challenge_id: int) -> dict:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
        return dict(row) if row else None


def deactivate_challenge(challenge_id: int):
    with _lock, _connect() as conn:
        conn.execute("UPDATE challenges SET active = 0 WHERE id = ?", (challenge_id,))
        conn.commit()


def submit_challenge(challenge_id: int, user_id: int, note: str) -> int:
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO challenge_submissions (challenge_id, user_id, note) VALUES (?, ?, ?)",
            (challenge_id, user_id, note),
        )
        conn.commit()
        return cur.lastrowid


def get_pending_submissions() -> list[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM challenge_submissions WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_submission(submission_id: int) -> dict:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM challenge_submissions WHERE id = ?", (submission_id,)).fetchone()
        return dict(row) if row else None


def review_submission(submission_id: int, status: str, reviewed_by: int):
    with _lock, _connect() as conn:
        conn.execute("""
            UPDATE challenge_submissions
            SET status = ?, reviewed_by = ?, reviewed_at = datetime('now')
            WHERE id = ?
        """, (status, reviewed_by, submission_id))
        conn.commit()


# ---- rewards catalog ----

def add_reward(name: str, description: str, cost: int) -> int:
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO rewards_catalog (name, description, cost) VALUES (?, ?, ?)",
            (name, description, cost),
        )
        conn.commit()
        return cur.lastrowid


def get_active_rewards() -> list[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM rewards_catalog WHERE active = 1 ORDER BY cost ASC").fetchall()
        return [dict(r) for r in rows]


def get_reward(reward_id: int) -> dict:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM rewards_catalog WHERE id = ?", (reward_id,)).fetchone()
        return dict(row) if row else None


def deactivate_reward(reward_id: int):
    with _lock, _connect() as conn:
        conn.execute("UPDATE rewards_catalog SET active = 0 WHERE id = ?", (reward_id,))
        conn.commit()


# ---- redemption requests ----

def create_redemption_request(reward_id: int, user_id: int, cost: int) -> int:
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO redemption_requests (reward_id, user_id, cost) VALUES (?, ?, ?)",
            (reward_id, user_id, cost),
        )
        conn.commit()
        return cur.lastrowid


def get_pending_redemptions() -> list[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM redemption_requests WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_redemption(redemption_id: int) -> dict:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM redemption_requests WHERE id = ?", (redemption_id,)).fetchone()
        return dict(row) if row else None


def set_redemption_status(redemption_id: int, status: str, reviewed_by: int):
    with _lock, _connect() as conn:
        conn.execute("""
            UPDATE redemption_requests
            SET status = ?, fulfilled_by = ?, fulfilled_at = datetime('now')
            WHERE id = ?
        """, (status, reviewed_by, redemption_id))
        conn.commit()
