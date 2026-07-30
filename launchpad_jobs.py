"""
Scheduled jobs for Launchpad's twice-daily overview posts (morning/evening).

Same module-level bot-reference pattern as jobs.py, lifecycle_jobs.py, and
creator_jobs.py -- needed because these are recurring cron jobs registered
once with APScheduler's persistent job store, which pickles jobs by
reference rather than by live object.
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import launchpad_db

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


async def post_daily_overview(period: str):
    """period is 'morning' or 'evening'."""
    if _bot is None:
        print("post_daily_overview called before bot was ready; skipping.")
        return

    tz_name = os.getenv("BOT_TIMEZONE", "America/Chicago")
    today_iso = datetime.now(ZoneInfo(tz_name)).date().isoformat()

    day_number = launchpad_db.get_current_day(today_iso)
    if day_number is None:
        return  # no active cohort right now, or the 14 days have elapsed

    entry = launchpad_db.get_day(day_number)
    if not entry:
        print(f"post_daily_overview: no content stored for day {day_number}.")
        return

    channel_id = launchpad_db.get_channel_id()
    if not channel_id:
        print("post_daily_overview: no Launchpad channel configured.")
        return

    if period == "morning":
        emoji, greeting = "🌅", "Good morning"
    else:
        emoji, greeting = "🌙", "Evening check-in"

    overview = entry.get("overview") or entry["title"]
    if entry.get("thread_url"):
        thread_note = f"Head to {entry['thread_url']} and complete your missions!"
    else:
        thread_note = "Check today's thread and complete your missions!"

    text = (
        f"{emoji} {greeting}! Today is **Day {day_number}: {entry['title']}**\n\n"
        f"{overview}\n\n{thread_note}"
    )

    for guild in _bot.guilds:
        channel = guild.get_channel(channel_id)
        if channel is None:
            continue
        try:
            await channel.send(text)
        except Exception as e:
            print(f"Failed to post Launchpad {period} overview: {e}")
