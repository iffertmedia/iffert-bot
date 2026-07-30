"""
Functions the scheduler calls for lifecycle messaging follow-ups, plus the
shared template-rendering helper used by both the scheduled job and the
on-demand slash commands.

Like jobs.py, this needs a module-level bot reference rather than taking the
bot as an argument, since APScheduler's persistent job store pickles jobs by
reference (module path + function name), not by live object.
"""

import asyncio
import os
from zoneinfo import ZoneInfo
import discord

import messaging_db

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


def render_template(template: str, event=None, member=None) -> str:
    text = template
    if event is not None:
        text = text.replace("{event_name}", event.name)
        if event.start_time:
            # Discord's API always returns start_time in UTC; convert to the
            # configured local timezone before formatting for display,
            # otherwise every event time shown to people is off by however
            # many hours UTC is ahead of them.
            tz_name = os.getenv("BOT_TIMEZONE", "America/Chicago")
            local_start = event.start_time.astimezone(ZoneInfo(tz_name))
            text = text.replace("{event_date}", local_start.strftime("%B %d"))
            text = text.replace("{event_time}", local_start.strftime("%I:%M %p"))
    if member is not None:
        name = getattr(member, "display_name", None) or str(member)
        text = text.replace("{user_name}", name)
    return text


async def _send_to_registrants(guild, event, event_id: int, template: str, label: str):
    """Shared send loop used by both the reminder and follow up jobs."""
    user_ids = messaging_db.get_registrants(event_id)
    sent, failed = 0, []
    for user_id in user_ids:
        member = guild.get_member(user_id)
        if member is None:
            continue
        text = render_template(template, event=event, member=member)
        try:
            await member.send(text)
            sent += 1
        except Exception:
            failed.append(member.display_name)
        await asyncio.sleep(1)  # gentle pacing to avoid Discord DM rate limits

    event_name = event.name if event else f"event {event_id}"
    summary = f"{label} for **{event_name}**: {sent} delivered."
    if failed:
        shown = ", ".join(failed[:20])
        more = f" (+{len(failed) - 20} more)" if len(failed) > 20 else ""
        summary += f" Could not DM {len(failed)}: {shown}{more}"

    print(summary)
    log_channel_id = messaging_db.get_log_channel_id()
    if log_channel_id:
        channel = guild.get_channel(log_channel_id)
        if channel:
            try:
                await channel.send(summary)
            except Exception as e:
                print(f"Failed to post {label.lower()} summary to log channel: {e}")


async def send_reminder_job(guild_id: int, event_id: int):
    """Called by the scheduler shortly before an event starts."""
    if _bot is None:
        print("send_reminder_job called before bot was ready; skipping.")
        return
    guild = _bot.get_guild(guild_id)
    if guild is None:
        print(f"send_reminder_job: guild {guild_id} not found.")
        return

    event = guild.get_scheduled_event(event_id)
    if event is not None and event.status != discord.EventStatus.scheduled:
        return  # event got canceled or already started/ended before the reminder fired

    cfg = messaging_db.get_event_config(event_id)
    template = cfg.get("reminder_message") or messaging_db.get_default_reminder_message()
    await _send_to_registrants(guild, event, event_id, template, "⏰ Reminder sent")


async def send_followups_job(guild_id: int, event_id: int):
    """Called by the scheduler once an event's follow-up delay has elapsed."""
    if _bot is None:
        print("send_followups_job called before bot was ready; skipping.")
        return

    guild = _bot.get_guild(guild_id)
    if guild is None:
        print(f"send_followups_job: guild {guild_id} not found.")
        return

    event = guild.get_scheduled_event(event_id)
    cfg = messaging_db.get_event_config(event_id)
    template = cfg.get("followup_message") or messaging_db.get_default_followup_message()
    await _send_to_registrants(guild, event, event_id, template, "📨 Follow up sent")
