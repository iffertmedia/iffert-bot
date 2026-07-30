"""
Persistence for creator role management: level->role mappings, the Launchpad
completion role, announcement channels, message templates, and self-reported
birthdays. Same lightweight sqlite3 pattern as messaging_db.py, kept as its
own file/module since it's a distinct feature area.
"""

import os
import sqlite3
import threading

DB_PATH = os.path.join("data", "creator.db")
_lock = threading.Lock()

LEVELS = ["GO Creator", "L1", "L2", "L3", "L4", "L5", "L6"]
COHORTS = ["Green", "Purple", "Red"]  # Launchpad cohort roles, removed once someone is certified

DEFAULT_WELCOME_DM = (
    "Welcome to Iffert Media, {user_name}! We're glad you're here. "
    "Take a look around and let us know if you have any questions."
)
DEFAULT_LEVEL_DM = "Congrats {user_name}, you've been leveled up to {level}! Keep up the great work."
DEFAULT_LEVEL_ANNOUNCE = "🎉 {user_name} just leveled up to {level}!"
DEFAULT_CERTIFY_DM = "Congrats on completing Launchpad, {user_name}! You're all set."
DEFAULT_CERTIFY_ANNOUNCE = "🎓 {user_name} just completed Launchpad!"
DEFAULT_BIRTHDAY_ANNOUNCE = "🎂 Happy birthday, {user_name}!"


def _connect() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS birthdays (
                user_id INTEGER PRIMARY KEY,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL
            )
        """)
        conn.commit()


# ---- generic settings ----

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


# ---- level roles ----

def get_level_role_id(level: str):
    val = get_setting(f"level_role_{level}")
    return int(val) if val else None


def set_level_role_id(level: str, role_id: int):
    set_setting(f"level_role_{level}", str(role_id))


def get_all_level_role_ids() -> dict:
    return {lvl: get_level_role_id(lvl) for lvl in LEVELS}


# ---- launchpad cohort roles (Green/Purple/Red -- removed once someone gets GO Creator) ----

def get_cohort_role_id(cohort: str):
    val = get_setting(f"cohort_role_{cohort}")
    return int(val) if val else None


def set_cohort_role_id(cohort: str, role_id: int):
    set_setting(f"cohort_role_{cohort}", str(role_id))


def get_all_cohort_role_ids() -> dict:
    return {c: get_cohort_role_id(c) for c in COHORTS}


# ---- announcement channels ----

def get_channel_setting(name: str):
    val = get_setting(f"{name}_channel_id")
    return int(val) if val else None


def set_channel_setting(name: str, channel_id: int):
    set_setting(f"{name}_channel_id", str(channel_id))


# ---- message templates ----

def get_default_welcome_dm() -> str:
    return get_setting("welcome_dm_template", DEFAULT_WELCOME_DM)


def get_default_level_dm() -> str:
    return get_setting("level_dm_template", DEFAULT_LEVEL_DM)


def get_default_level_announce() -> str:
    return get_setting("level_announce_template", DEFAULT_LEVEL_ANNOUNCE)


def get_default_certify_dm() -> str:
    return get_setting("certify_dm_template", DEFAULT_CERTIFY_DM)


def get_default_certify_announce() -> str:
    return get_setting("certify_announce_template", DEFAULT_CERTIFY_ANNOUNCE)


def get_default_birthday_announce() -> str:
    return get_setting("birthday_announce_template", DEFAULT_BIRTHDAY_ANNOUNCE)


# ---- birthdays (self-reported, no year -- just month/day) ----

def set_birthday(user_id: int, month: int, day: int):
    with _lock, _connect() as conn:
        conn.execute("""
            INSERT INTO birthdays (user_id, month, day) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET month = excluded.month, day = excluded.day
        """, (user_id, month, day))
        conn.commit()


def get_birthday(user_id: int):
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT month, day FROM birthdays WHERE user_id = ?", (user_id,)
        ).fetchone()
        return (row["month"], row["day"]) if row else None


def get_birthdays_for_date(month: int, day: int) -> list[int]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT user_id FROM birthdays WHERE month = ? AND day = ?", (month, day)
        ).fetchall()
        return [r["user_id"] for r in rows]
