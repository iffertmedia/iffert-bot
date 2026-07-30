from datetime import date

import discord
from discord import app_commands
from discord.ext import commands
from apscheduler.triggers.cron import CronTrigger

import launchpad_db
import launchpad_jobs
from launchpad_content import SEED_DAYS

DISCORD_MESSAGE_LIMIT = 1900


def chunk_text(text: str, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """Split text into Discord-safe chunks, breaking on blank lines where possible."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            if len(paragraph) > limit:
                for i in range(0, len(paragraph), limit):
                    chunks.append(paragraph[i:i + limit])
                current = ""
            else:
                current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


class Launchpad(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        launchpad_jobs.set_bot(bot)

    async def cog_load(self):
        # Fixed ids + replace_existing so restarts don't create duplicate
        # recurring jobs. Persists via the same disk-backed scheduler as
        # everything else, so these survive a redeploy.
        self.bot.scheduler.add_job(
            launchpad_jobs.post_daily_overview,
            trigger=CronTrigger(hour=9, minute=0),
            kwargs={"period": "morning"},
            id="launchpad-morning",
            replace_existing=True,
        )
        self.bot.scheduler.add_job(
            launchpad_jobs.post_daily_overview,
            trigger=CronTrigger(hour=17, minute=0),
            kwargs={"period": "evening"},
            id="launchpad-evening",
            replace_existing=True,
        )

    @app_commands.command(
        name="launchpad",
        description="Manually post a day's full content (e.g. into a thread). Not the daily reminder.",
    )
    @app_commands.describe(day="Day number (1-14)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def launchpad(self, interaction: discord.Interaction, day: app_commands.Range[int, 1, 14]):
        entry = launchpad_db.get_day(day)
        if not entry:
            await interaction.response.send_message(f"⚠️ Day {day} has no content yet.", ephemeral=True)
            return

        channel_id = launchpad_db.get_channel_id()
        if not channel_id:
            await interaction.response.send_message(
                "⚠️ No Launchpad channel is configured. Run `/launchpad_channel` first.", ephemeral=True
            )
            return
        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(
                "⚠️ The configured Launchpad channel no longer exists. Run `/launchpad_channel` to fix it.",
                ephemeral=True,
            )
            return

        header = f"# Day {day}: {entry['title']}\n\n"
        chunks = chunk_text(header + entry["content"])
        for chunk in chunks:
            await channel.send(chunk)

        await interaction.response.send_message(f"✅ Posted Day {day} to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="launchpad_preview", description="Preview a Launchpad day's content privately before posting it live.")
    @app_commands.describe(day="Day number (1-14)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def launchpad_preview(self, interaction: discord.Interaction, day: app_commands.Range[int, 1, 14]):
        entry = launchpad_db.get_day(day)
        if not entry:
            await interaction.response.send_message(f"⚠️ Day {day} has no content yet.", ephemeral=True)
            return

        header = f"# Day {day}: {entry['title']}\n\n"
        chunks = chunk_text(header + entry["content"])
        await interaction.response.send_message(chunks[0], ephemeral=True)
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk, ephemeral=True)

    @app_commands.command(name="launchpad_list", description="List all 14 Launchpad days and their titles.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def launchpad_list(self, interaction: discord.Interaction):
        days = launchpad_db.get_all_days()
        lines = [f"Day {d['day_number']}: {d['title']} ({len(d['content'])} chars)" for d in days]
        await interaction.response.send_message("**Launchpad curriculum**\n" + "\n".join(lines), ephemeral=True)

    @app_commands.command(
        name="launchpad_day_edit",
        description="Edit a Launchpad day's content by uploading a text file (avoids Discord's text length limits).",
    )
    @app_commands.describe(
        day="Day number (1-14)",
        title="New title for this day",
        file="A .txt file with the new content (upload one from your computer)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def launchpad_day_edit(
        self, interaction: discord.Interaction, day: app_commands.Range[int, 1, 14],
        title: str, file: discord.Attachment,
    ):
        if not (file.content_type or "").startswith("text/"):
            await interaction.response.send_message(
                "⚠️ Please upload a plain .txt file.", ephemeral=True
            )
            return

        try:
            raw = await file.read()
            content = raw.decode("utf-8")
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Couldn't read that file: {e}", ephemeral=True)
            return

        launchpad_db.set_day(day, title, content)
        await interaction.response.send_message(
            f"✅ Day {day} updated: **{title}** ({len(content)} chars).", ephemeral=True
        )

    @app_commands.command(name="launchpad_channel", description="Set the channel where Launchpad content gets posted.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def launchpad_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        launchpad_db.set_setting("channel_id", str(channel.id))
        await interaction.response.send_message(f"✅ Launchpad content will post in {channel.mention}.", ephemeral=True)

    @app_commands.command(
        name="launchpad_start_cohort",
        description="Start a new cohort: marks today as Day 1 and begins the twice-daily reminders.",
    )
    @app_commands.describe(start_date="Optional: YYYY-MM-DD if Day 1 isn't today (defaults to today)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def launchpad_start_cohort(self, interaction: discord.Interaction, start_date: str = None):
        if start_date:
            try:
                date.fromisoformat(start_date)
            except ValueError:
                await interaction.response.send_message(
                    "⚠️ Use YYYY-MM-DD format, e.g. 2026-08-03.", ephemeral=True
                )
                return
        else:
            start_date = date.today().isoformat()

        launchpad_db.start_cohort(start_date)
        await interaction.response.send_message(
            f"✅ Cohort started. {start_date} is Day 1 — the 9am/5pm reminders will begin tracking from there "
            f"through Day 14.",
            ephemeral=True,
        )

    @app_commands.command(name="launchpad_status", description="Check the current cohort's day and start date.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def launchpad_status(self, interaction: discord.Interaction):
        start = launchpad_db.get_cohort_start_date()
        if not start:
            await interaction.response.send_message(
                "No cohort is currently active. Run `/launchpad_start_cohort` to begin one.", ephemeral=True
            )
            return

        today_iso = date.today().isoformat()
        current_day = launchpad_db.get_current_day(today_iso)
        if current_day is None:
            await interaction.response.send_message(
                f"Cohort started {start}, but that's more than 14 days ago — the program has finished. "
                f"Run `/launchpad_start_cohort` to begin a new one.",
                ephemeral=True,
            )
            return

        entry = launchpad_db.get_day(current_day)
        title = entry["title"] if entry else "unknown"
        await interaction.response.send_message(
            f"Cohort started {start}. Today is **Day {current_day}: {title}**.", ephemeral=True
        )

    @app_commands.command(
        name="launchpad_day_thread",
        description="Set the thread link for a day, included in that day's reminder posts.",
    )
    @app_commands.describe(day="Day number (1-14)", thread_url="The thread's link")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def launchpad_day_thread(
        self, interaction: discord.Interaction, day: app_commands.Range[int, 1, 14], thread_url: str
    ):
        launchpad_db.set_day(day, thread_url=thread_url)
        await interaction.response.send_message(f"✅ Day {day}'s reminder will now link to {thread_url}.", ephemeral=True)

    @app_commands.command(
        name="launchpad_overview_edit",
        description="Edit a day's short overview blurb used in the 9am/5pm reminder posts.",
    )
    @app_commands.describe(day="Day number (1-14)", overview="The new short overview (1-2 sentences)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def launchpad_overview_edit(
        self, interaction: discord.Interaction, day: app_commands.Range[int, 1, 14], overview: str
    ):
        launchpad_db.set_day(day, overview=overview)
        await interaction.response.send_message(f"✅ Day {day}'s overview updated.", ephemeral=True)


async def setup(bot: commands.Bot):
    launchpad_db.init_db()
    launchpad_db.seed_if_empty(SEED_DAYS)
    launchpad_db.backfill_missing_overviews(SEED_DAYS)
    await bot.add_cog(Launchpad(bot))
