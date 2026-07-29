"""
Parsing helpers for /schedule and /every.

Kept deliberately simple for the MVP: a handful of clear formats rather
than a full natural-language parser. Easy to extend later.
"""

from datetime import datetime

DAY_NAMES = {
    "monday": "mon", "mon": "mon",
    "tuesday": "tue", "tue": "tue", "tues": "tue",
    "wednesday": "wed", "wed": "wed",
    "thursday": "thu", "thu": "thu", "thurs": "thu",
    "friday": "fri", "fri": "fri",
    "saturday": "sat", "sat": "sat",
    "sunday": "sun", "sun": "sun",
}

TIME_FORMATS = ["%I:%M%p", "%I%p", "%H:%M", "%I:%M %p", "%I %p"]


class ParseError(ValueError):
    pass


def parse_time_str(time_str: str) -> tuple[int, int]:
    """Parse '8am', '8:00 AM', '08:00' -> (hour, minute) in 24h time."""
    cleaned = time_str.strip().replace(" ", "")
    # re-insert a single space before am/pm variants so both '8am' and '8 am' work
    for fmt in TIME_FORMATS:
        try:
            dt = datetime.strptime(cleaned, fmt.replace(" ", ""))
            return dt.hour, dt.minute
        except ValueError:
            continue
    raise ParseError(
        f"Couldn't understand time '{time_str}'. Try formats like '8am', '8:00 AM', or '17:30'."
    )


def parse_date_str(date_str: str) -> tuple[int, int, int]:
    """Parse 'August 5' 'Aug 5 2026' '2026-08-05' '08/05/2026' -> (year, month, day)."""
    cleaned = date_str.strip()
    now = datetime.now()
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%B %d %Y", "%B %d", "%b %d %Y", "%b %d", "%m/%d"]
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            year = dt.year if dt.year != 1900 else now.year
            return year, dt.month, dt.day
        except ValueError:
            continue
    raise ParseError(
        f"Couldn't understand date '{date_str}'. Try 'August 5', '2026-08-05', or '08/05/2026'."
    )


def parse_recurrence(recurrence_str: str) -> dict:
    """
    Parse strings like:
      'monday 9am'   -> weekly on Monday at 9:00
      'day 8am'      -> every day at 8:00
      'friday 5pm'   -> weekly on Friday at 17:00
      'first sunday' -> first Sunday of each month (time defaults to 9am unless given)

    Returns kwargs suitable for APScheduler's CronTrigger.
    """
    text = recurrence_str.strip().lower()
    parts = text.split()
    if not parts:
        raise ParseError("Recurrence string was empty.")

    # "first sunday [9am]" style
    if parts[0] in ("first", "second", "third", "fourth", "last"):
        if len(parts) < 2 or parts[1] not in DAY_NAMES:
            raise ParseError(
                f"Couldn't understand recurrence '{recurrence_str}'. "
                "Try 'first sunday' or 'first sunday 9am'."
            )
        day = DAY_NAMES[parts[1]]
        hour, minute = (9, 0)
        if len(parts) > 2:
            hour, minute = parse_time_str(parts[2])
        ordinal_map = {"first": "1", "second": "2", "third": "3", "fourth": "4", "last": "last"}
        return {
            "day_of_week": day,
            "hour": hour,
            "minute": minute,
            # APScheduler cron doesn't natively do "nth weekday of month" --
            # this is stored as metadata; see NOTE in scheduler.py for the caveat.
            "_ordinal": ordinal_map[parts[0]],
        }

    # "day 8am" -> every day
    if parts[0] == "day":
        if len(parts) < 2:
            raise ParseError("Missing a time, e.g. 'day 8am'.")
        hour, minute = parse_time_str(parts[1])
        return {"day_of_week": "*", "hour": hour, "minute": minute}

    # "monday 9am" -> weekly
    if parts[0] in DAY_NAMES:
        if len(parts) < 2:
            raise ParseError(f"Missing a time, e.g. '{parts[0]} 9am'.")
        hour, minute = parse_time_str(parts[1])
        return {"day_of_week": DAY_NAMES[parts[0]], "hour": hour, "minute": minute}

    raise ParseError(
        f"Couldn't understand recurrence '{recurrence_str}'. "
        "Try 'monday 9am', 'day 8am', or 'first sunday 9am'."
    )
