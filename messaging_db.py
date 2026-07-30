"""
Persistence for lifecycle messaging: per-event message templates, the
registrant roster for each scheduled event (captured as people RSVP, since
Discord's API may not reliably return the roster once an event completes),
and dedupe tracking so registration DMs and follow ups never double-send.

Uses plain sqlite3 rather than the ORM-based scheduler DB -- these are tiny,
fast, infrequent operations, not worth the extra dependency weight.
"""

import os
import sqlite3
import threading

DB_PATH = os.path.join("data", "messaging.db")
_lock = threading.Lock()

DEFAULT_REGISTRATION_MESSAGE = (
    "Hey {user_name}! You're registered for {event_name} on {event_date} at "
    "{event_time}. See you there!"
)
DEFAULT_FOLLOWUP_MESSAGE = (
    "Hey {user_name}, thanks for coming to {event_name}! Let us know if you "
    "have any feedback."
)
DEFAULT_FOLLOWUP_DELAY_MINUTES = 0


def _connect() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS event_config (
                event_id INTEGER PRIMARY KEY,
                registration_message TEXT,
                followup_message TEXT,
                followup_delay_minutes INTEGER,
                followup_scheduled INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS event_registrants (
                event_id INTEGER,
                user_id INTEGER,
                registration_dm_sent INTEGER DEFAULT 0,
                PRIMARY KEY (event_id, user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()


# ---- global default templates ----

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


def get_default_registration_message() -> str:
    return get_setting("default_registration_message", DEFAULT_REGISTRATION_MESSAGE)


def get_default_followup_message() -> str:
    return get_setting("default_followup_message", DEFAULT_FOLLOWUP_MESSAGE)


def get_default_followup_delay() -> int:
    return int(get_setting("default_followup_delay_minutes", str(DEFAULT_FOLLOWUP_DELAY_MINUTES)))


def get_log_channel_id():
    val = get_setting("log_channel_id")
    return int(val) if val else None


# ---- per-event overrides ----

def set_event_config(event_id: int, registration_message: str = None,
                      followup_message: str = None, followup_delay_minutes: int = None):
    with _lock, _connect() as conn:
        conn.execute("""
            INSERT INTO event_config (event_id, registration_message, followup_message, followup_delay_minutes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                registration_message = COALESCE(excluded.registration_message, event_config.registration_message),
                followup_message = COALESCE(excluded.followup_message, event_config.followup_message),
                followup_delay_minutes = COALESCE(excluded.followup_delay_minutes, event_config.followup_delay_minutes)
        """, (event_id, registration_message, followup_message, followup_delay_minutes))
        conn.commit()


def get_event_config(event_id: int) -> dict:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM event_config WHERE event_id = ?", (event_id,)).fetchone()
        return dict(row) if row else {}


def mark_followup_scheduled(event_id: int):
    with _lock, _connect() as conn:
        conn.execute("""
            INSERT INTO event_config (event_id, followup_scheduled) VALUES (?, 1)
            ON CONFLICT(event_id) DO UPDATE SET followup_scheduled = 1
        """, (event_id,))
        conn.commit()


def is_followup_scheduled(event_id: int) -> bool:
    return bool(get_event_config(event_id).get("followup_scheduled"))


# ---- registrant roster (captured live, since it may not be queryable after event completion) ----

def add_registrant(event_id: int, user_id: int):
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO event_registrants (event_id, user_id) VALUES (?, ?)",
            (event_id, user_id),
        )
        conn.commit()


def remove_registrant(event_id: int, user_id: int):
    with _lock, _connect() as conn:
        conn.execute(
            "DELETE FROM event_registrants WHERE event_id = ? AND user_id = ?",
            (event_id, user_id),
        )
        conn.commit()


def mark_registration_dm_sent(event_id: int, user_id: int):
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE event_registrants SET registration_dm_sent = 1 WHERE event_id = ? AND user_id = ?",
            (event_id, user_id),
        )
        conn.commit()


def has_sent_registration_dm(event_id: int, user_id: int) -> bool:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT registration_dm_sent FROM event_registrants WHERE event_id = ? AND user_id = ?",
            (event_id, user_id),
        ).fetchone()
        return bool(row and row["registration_dm_sent"])


def get_registrants(event_id: int) -> list[int]:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT user_id FROM event_registrants WHERE event_id = ?", (event_id,)
        ).fetchall()
        return [r["user_id"] for r in rows]
