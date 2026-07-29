"""
Functions that scheduled jobs actually call.

APScheduler's SQLAlchemyJobStore pickles jobs to disk by *reference*
(module path + function name), not the live bot object. That means these
functions can't take the bot as an argument -- they need to look it up
from a module-level variable that gets set once at startup instead.
"""

import discord

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


async def post_message(channel_id: int, message: str):
    """Called by the scheduler (one-time or recurring) to post to a channel."""
    if _bot is None:
        print("post_message called before bot was ready; skipping.")
        return

    channel = _bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await _bot.fetch_channel(channel_id)
        except discord.NotFound:
            print(f"Channel {channel_id} not found (deleted or bot removed).")
            return
        except Exception as e:
            print(f"Failed to fetch channel {channel_id}: {e}")
            return

    try:
        await channel.send(message)
    except Exception as e:
        print(f"Failed to send scheduled message to channel {channel_id}: {e}")


async def post_message_if_nth_weekday(channel_id: int, message: str, ordinal: str):
    """
    Used for recurrence like 'first sunday'. APScheduler's cron trigger can't
    express 'nth weekday of month' directly, so this runs every week on the
    right day and only actually posts when it's the correct occurrence.
    """
    from datetime import datetime

    now = datetime.now()
    week_of_month = (now.day - 1) // 7 + 1  # 1st, 2nd, 3rd, 4th occurrence
    is_last = (now.day + 7) > _days_in_month(now.year, now.month)

    if ordinal == "last":
        if not is_last:
            return
    else:
        if str(week_of_month) != ordinal:
            return

    await post_message(channel_id, message)


def _days_in_month(year: int, month: int) -> int:
    import calendar
    return calendar.monthrange(year, month)[1]

