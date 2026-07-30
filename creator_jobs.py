"""
Bot reference and shared helpers for creator management, plus the daily
birthday check job. Same module-level-reference pattern as jobs.py and
lifecycle_jobs.py, needed because APScheduler's persistent job store pickles
jobs by reference, not by live object.
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import creator_db

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


def render(template: str, member=None, level: str = None) -> str:
    text = template
    if member is not None:
        name = getattr(member, "display_name", None) or str(member)
        text = text.replace("{user_name}", name)
    if level is not None:
        text = text.replace("{level}", level)
    return text


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


async def daily_birthday_check():
    """Runs once a day (scheduled in cogs/creator_management.py). Posts a
    shoutout in the configured channel for anyone whose birthday is today."""
    if _bot is None:
        print("daily_birthday_check called before bot was ready; skipping.")
        return

    tz_name = os.getenv("BOT_TIMEZONE", "America/Chicago")
    today = datetime.now(ZoneInfo(tz_name))
    month, day = today.month, today.day

    user_ids = creator_db.get_birthdays_for_date(month, day)
    # Feb 29 birthdays: celebrate on Feb 28 in non-leap years so they aren't skipped.
    if month == 2 and day == 28 and not _is_leap_year(today.year):
        user_ids = list(user_ids) + creator_db.get_birthdays_for_date(2, 29)

    if not user_ids:
        return

    channel_id = creator_db.get_channel_setting("birthday_announce")
    if not channel_id:
        print("Birthday check found birthdays today but no birthday_announce channel is configured.")
        return

    template = creator_db.get_default_birthday_announce()
    for guild in _bot.guilds:
        channel = guild.get_channel(channel_id)
        if channel is None:
            continue
        for user_id in user_ids:
            member = guild.get_member(user_id)
            if member is None:
                continue
            text = render(template, member=member)
            try:
                await channel.send(text)
            except Exception as e:
                print(f"Failed to post birthday announcement: {e}")
