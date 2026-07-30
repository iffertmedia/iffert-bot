"""
Persistence for engagement analytics: messages sent, reactions given, and
voice/stage channel time, aggregated per member per day.

Design choice: one row per (user, day) with running counts, not one row per
raw event. A server generates a lot of messages and reactions over time --
logging every single one forever would make the database grow without
bound. Daily aggregates are the right shape for a long-running tracker:
bounded by (number of members) x (number of days), and still flexible
enough to answer "last 7 days" / "last 30 days" / "this month" by summing
across the relevant day-rows.
"""

import os
import sqlite3
import threading

DB_PATH = os.path.join("data", "analytics.db")
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_activity (
                user_id INTEGER NOT NULL,
                activity_date TEXT NOT NULL,
                messages INTEGER DEFAULT 0,
                reactions_given INTEGER DEFAULT 0,
                voice_seconds INTEGER DEFAULT 0,
                voice_joins INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, activity_date)
            )
        """)
        # Tracks voice/stage sessions currently in progress, so duration can
        # be computed correctly on leave even across a bot restart (the
        # join timestamp survives since it's on disk, not just in memory).
        conn.execute("""
            CREATE TABLE IF NOT EXISTS voice_sessions (
                user_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                joined_at TEXT NOT NULL
            )
        """)
        conn.commit()


def _bump(user_id: int, activity_date: str, column: str, amount: int = 1):
    with _lock, _connect() as conn:
        conn.execute(f"""
            INSERT INTO daily_activity (user_id, activity_date, {column})
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, activity_date) DO UPDATE SET
                {column} = {column} + excluded.{column}
        """, (user_id, activity_date, amount))
        conn.commit()


def record_message(user_id: int, activity_date: str):
    _bump(user_id, activity_date, "messages")


def record_reaction(user_id: int, activity_date: str):
    _bump(user_id, activity_date, "reactions_given")


def record_voice_time(user_id: int, activity_date: str, seconds: int):
    _bump(user_id, activity_date, "voice_seconds", seconds)


def record_voice_join(user_id: int, activity_date: str):
    _bump(user_id, activity_date, "voice_joins")


# ---- voice session tracking (join -> leave duration) ----

def start_voice_session(user_id: int, channel_id: int, joined_at_iso: str):
    with _lock, _connect() as conn:
        conn.execute("""
            INSERT INTO voice_sessions (user_id, channel_id, joined_at) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET channel_id = excluded.channel_id, joined_at = excluded.joined_at
        """, (user_id, channel_id, joined_at_iso))
        conn.commit()


def get_voice_session(user_id: int):
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM voice_sessions WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def end_voice_session(user_id: int):
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM voice_sessions WHERE user_id = ?", (user_id,))
        conn.commit()


# ---- reporting ----

def get_totals_for_user(user_id: int, start_date: str, end_date: str) -> dict:
    with _lock, _connect() as conn:
        row = conn.execute("""
            SELECT COALESCE(SUM(messages), 0) AS messages,
                   COALESCE(SUM(reactions_given), 0) AS reactions_given,
                   COALESCE(SUM(voice_seconds), 0) AS voice_seconds,
                   COALESCE(SUM(voice_joins), 0) AS voice_joins
            FROM daily_activity
            WHERE user_id = ? AND activity_date BETWEEN ? AND ?
        """, (user_id, start_date, end_date)).fetchone()
        return dict(row)


VALID_METRICS = {"messages", "reactions_given", "voice_seconds"}


def get_leaderboard(metric: str, start_date: str, end_date: str, limit: int = 10) -> list[tuple]:
    """metric is one of: messages, reactions_given, voice_seconds."""
    if metric not in VALID_METRICS:
        raise ValueError(f"Invalid metric: {metric}")
    with _lock, _connect() as conn:
        rows = conn.execute(f"""
            SELECT user_id, SUM({metric}) AS total
            FROM daily_activity
            WHERE activity_date BETWEEN ? AND ?
            GROUP BY user_id
            HAVING total > 0
            ORDER BY total DESC
            LIMIT ?
        """, (start_date, end_date, limit)).fetchall()
        return [(r["user_id"], r["total"]) for r in rows]
