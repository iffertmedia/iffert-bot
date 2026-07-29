from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

import jobs
from cogs.time_parsing import parse_date_str, parse_time_str, parse_recurrence, ParseError


class MessageModal(discord.ui.Modal):
    """Collects the message body -- kept as a modal since posts are often multi-line."""

    message_input = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.paragraph,
        placeholder="Good morning Launchpad Crew!\nToday's mission is...",
        required=True,
        max_length=2000,
    )

    def __init__(self, title: str, on_submit_callback):
        super().__init__(title=title)
        self._on_submit_callback = on_submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self._on_submit_callback(interaction, str(self.message_input.value))


class Scheduler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="schedule", description="Schedule a one-time message to post later.")
    @app_commands.describe(
        channel="Channel to post in",
        date="e.g. 'August 5', '2026-08-05', '08/05/2026'",
        time="e.g. '8:00 AM', '8am', '17:30'",
    )
    async def schedule(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        date: str,
        time: str,
    ):
        try:
            year, month, day = parse_date_str(date)
            hour, minute = parse_time_str(time)
            run_date = datetime(year, month, day, hour, minute)
        except ParseError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        except ValueError:
            await interaction.response.send_message(
                "⚠️ That date doesn't exist. Double check the day/month.", ephemeral=True
            )
            return

        if run_date < datetime.now():
            await interaction.response.send_message(
                "⚠️ That date/time is in the past.", ephemeral=True
            )
            return

        async def on_submit(modal_interaction: discord.Interaction, message: str):
            job = self.bot.scheduler.add_job(
                jobs.post_message,
                trigger=DateTrigger(run_date=run_date),
                kwargs={"channel_id": channel.id, "message": message},
                id=f"schedule-{modal_interaction.id}",
            )
            await modal_interaction.response.send_message(
                f"✅ Scheduled for **{run_date.strftime('%B %d, %Y at %I:%M %p')}** "
                f"in {channel.mention}.\nJob ID: `{job.id}`",
                ephemeral=True,
            )

        await interaction.response.send_modal(
            MessageModal(title=f"Message for {run_date.strftime('%b %d, %I:%M %p')}", on_submit_callback=on_submit)
        )

    @app_commands.command(name="every", description="Schedule a recurring message.")
    @app_commands.describe(
        channel="Channel to post in",
        recurrence="e.g. 'monday 9am', 'day 8am', 'friday 5pm', 'first sunday 9am'",
    )
    async def every(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        recurrence: str,
    ):
        try:
            parsed = parse_recurrence(recurrence)
        except ParseError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        ordinal = parsed.pop("_ordinal", None)

        async def on_submit(modal_interaction: discord.Interaction, message: str):
            job_id = f"every-{modal_interaction.id}"
            if ordinal:
                job = self.bot.scheduler.add_job(
                    jobs.post_message_if_nth_weekday,
                    trigger=CronTrigger(day_of_week=parsed["day_of_week"], hour=parsed["hour"], minute=parsed["minute"]),
                    kwargs={"channel_id": channel.id, "message": message, "ordinal": ordinal},
                    id=job_id,
                )
            else:
                job = self.bot.scheduler.add_job(
                    jobs.post_message,
                    trigger=CronTrigger(**parsed),
                    kwargs={"channel_id": channel.id, "message": message},
                    id=job_id,
                )
            await modal_interaction.response.send_message(
                f"✅ Recurring message set for **{recurrence}** in {channel.mention}.\n"
                f"Job ID: `{job.id}` (use `/unschedule` to cancel it).",
                ephemeral=True,
            )

        await interaction.response.send_modal(
            MessageModal(title=f"Message for '{recurrence}'", on_submit_callback=on_submit)
        )

    @app_commands.command(name="unschedule", description="Cancel a scheduled or recurring message by job ID.")
    @app_commands.describe(job_id="The job ID shown when you created the schedule")
    async def unschedule(self, interaction: discord.Interaction, job_id: str):
        job = self.bot.scheduler.get_job(job_id)
        if job is None:
            await interaction.response.send_message(f"⚠️ No job found with ID `{job_id}`.", ephemeral=True)
            return
        job.remove()
        await interaction.response.send_message(f"🗑️ Cancelled job `{job_id}`.", ephemeral=True)

    @app_commands.command(name="scheduled", description="List all upcoming scheduled and recurring messages.")
    async def scheduled(self, interaction: discord.Interaction):
        jobs_list = self.bot.scheduler.get_jobs()
        if not jobs_list:
            await interaction.response.send_message("No messages are currently scheduled.", ephemeral=True)
            return

        lines = []
        for job in jobs_list:
            channel_id = job.kwargs.get("channel_id")
            channel = self.bot.get_channel(channel_id)
            channel_str = channel.mention if channel else f"`{channel_id}`"
            next_run = job.next_run_time.strftime("%b %d, %Y %I:%M %p") if job.next_run_time else "unknown"
            lines.append(f"`{job.id}` → {channel_str} — next run: {next_run}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Scheduler(bot))
