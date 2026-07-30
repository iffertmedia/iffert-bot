"""
Persistence for the Launchpad day-by-day curriculum.

Days are stored in the database, not hardcoded, so staff can edit content
without a redeploy. launchpad_content.py only provides the *initial* seed
values pulled from the real curriculum doc -- once a day exists in the
database, re-running the seed never overwrites it.
"""

import os
import sqlite3
import threading

DB_PATH = os.path.join("data", "launchpad.db")
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS launchpad_days (
                day_number INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT
            )
        """)
        # Migration: add columns for installs where this table already
        # existed before overview/thread tracking were added.
        for column_def in ("overview TEXT", "thread_url TEXT"):
            try:
                conn.execute(f"ALTER TABLE launchpad_days ADD COLUMN {column_def}")
            except sqlite3.OperationalError:
                pass  # column already exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()


def seed_if_empty(seed_days: dict):
    """Only inserts a day if it doesn't already exist -- never clobbers edits."""
    with _lock, _connect() as conn:
        for day_number, data in seed_days.items():
            conn.execute(
                "INSERT OR IGNORE INTO launchpad_days (day_number, title, content, overview) "
                "VALUES (?, ?, ?, ?)",
                (day_number, data["title"], data["content"], data.get("overview")),
            )
        conn.commit()


def backfill_missing_overviews(seed_days: dict):
    """
    For days that already existed before overview tracking was added (from
    an earlier deploy), fills in just the overview field without touching
    title/content -- so upgrading doesn't silently leave old days without
    a short blurb for the daily reminder posts.
    """
    with _lock, _connect() as conn:
        for day_number, data in seed_days.items():
            row = conn.execute(
                "SELECT overview FROM launchpad_days WHERE day_number = ?", (day_number,)
            ).fetchone()
            if row is not None and not row["overview"]:
                conn.execute(
                    "UPDATE launchpad_days SET overview = ? WHERE day_number = ?",
                    (data.get("overview"), day_number),
                )
        conn.commit()


def get_day(day_number: int):
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM launchpad_days WHERE day_number = ?", (day_number,)
        ).fetchone()
        return dict(row) if row else None


def set_day(day_number: int, title: str = None, content: str = None,
            overview: str = None, thread_url: str = None):
    """Partial update -- any field left as None keeps its current value."""
    with _lock, _connect() as conn:
        conn.execute("""
            INSERT INTO launchpad_days (day_number, title, content, overview, thread_url)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(day_number) DO UPDATE SET
                title = COALESCE(excluded.title, launchpad_days.title),
                content = COALESCE(excluded.content, launchpad_days.content),
                overview = COALESCE(excluded.overview, launchpad_days.overview),
                thread_url = COALESCE(excluded.thread_url, launchpad_days.thread_url)
        """, (day_number, title, content, overview, thread_url))
        conn.commit()


def get_all_days() -> list[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM launchpad_days ORDER BY day_number ASC").fetchall()
        return [dict(r) for r in rows]


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


def get_channel_id():
    val = get_setting("channel_id")
    return int(val) if val else None


# ---- cohort day tracking ----

def start_cohort(start_date_iso: str):
    """start_date_iso is the date (YYYY-MM-DD) that counts as Day 1."""
    set_setting("cohort_start_date", start_date_iso)


def get_cohort_start_date():
    return get_setting("cohort_start_date")


def get_current_day(today_iso: str):
    """
    Returns the current Launchpad day number (1-14) based on the cohort
    start date, or None if no cohort is active or the 14 days have elapsed.
    today_iso and the stored start date are both plain YYYY-MM-DD strings
    (timezone handling happens in the caller, using BOT_TIMEZONE) so this
    stays a pure date calculation with no timezone edge cases inside it.
    """
    from datetime import date

    start_iso = get_cohort_start_date()
    if not start_iso:
        return None

    start = date.fromisoformat(start_iso)
    today = date.fromisoformat(today_iso)
    day_number = (today - start).days + 1

    if 1 <= day_number <= 14:
        return day_number
    return None
