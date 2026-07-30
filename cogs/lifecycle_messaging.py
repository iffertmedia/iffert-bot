import asyncio
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.base import JobLookupError

import messaging_db
import lifecycle_jobs
from lifecycle_jobs import render_template


class BulkMessageModal(discord.ui.Modal):
    """Collects the message body for bulk-send commands -- a modal handles
    longer text better than a single-line slash command option."""

    message_input = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.paragraph,
        placeholder="Hey {user_name}, ...",
        required=True,
        max_length=2000,
    )

    def __init__(self, title: str, on_submit_callback):
        super().__init__(title=title)
        self._on_submit_callback = on_submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self._on_submit_callback(interaction, str(self.message_input.value))


async def event_autocomplete(interaction: discord.Interaction, current: str):
    if interaction.guild is None:
        return []
    current = current.lower()
    tz_name = os.getenv("BOT_TIMEZONE", "America/Chicago")
    choices = []
    for event in interaction.guild.scheduled_events:
        if current in event.name.lower():
            label = event.name
            if event.start_time:
                local_start = event.start_time.astimezone(ZoneInfo(tz_name))
                label += f" ({local_start.strftime('%b %d')})"
            choices.append(app_commands.Choice(name=label[:100], value=str(event.id)))
    return choices[:25]


class LifecycleMessaging(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        lifecycle_jobs.set_bot(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        # Catch-up scan: schedule reminders for any upcoming events that
        # don't already have one -- covers events created before this
        # feature existed, or while the bot was offline. Cheap to run on
        # every reconnect since _schedule_reminder just overwrites in place.
        for guild in self.bot.guilds:
            for event in guild.scheduled_events:
                if event.status == discord.EventStatus.scheduled:
                    self._schedule_reminder(event)

    def _schedule_reminder(self, event: discord.ScheduledEvent):
        """(Re)schedules the pre-event reminder job. Safe to call multiple
        times for the same event -- replace_existing means a reschedule
        (e.g. after the event's time changes) just overwrites the old one."""
        if event.start_time is None:
            return

        cfg = messaging_db.get_event_config(event.id)
        minutes_before = cfg.get("reminder_minutes_before")
        if minutes_before is None:
            minutes_before = messaging_db.get_default_reminder_minutes_before()

        now = datetime.now(event.start_time.tzinfo)
        if event.start_time <= now:
            return  # event already started/passed, nothing to remind about

        run_date = event.start_time - timedelta(minutes=minutes_before)
        if run_date <= now:
            run_date = now  # reminder window already passed -- send right away instead of skipping

        self.bot.scheduler.add_job(
            lifecycle_jobs.send_reminder_job,
            trigger=DateTrigger(run_date=run_date),
            kwargs={"guild_id": event.guild.id, "event_id": event.id},
            id=f"reminder-{event.id}",
            replace_existing=True,
        )

    def _cancel_reminder(self, event_id: int):
        try:
            self.bot.scheduler.remove_job(f"reminder-{event_id}")
        except JobLookupError:
            pass

    # ---- automatic listeners ----

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        self._schedule_reminder(event)

    @commands.Cog.listener()
    async def on_scheduled_event_user_add(self, event: discord.ScheduledEvent, user: discord.User):
        messaging_db.add_registrant(event.id, user.id)

        if messaging_db.has_sent_registration_dm(event.id, user.id):
            return

        cfg = messaging_db.get_event_config(event.id)
        template = cfg.get("registration_message") or messaging_db.get_default_registration_message()
        member = event.guild.get_member(user.id) or user
        text = render_template(template, event=event, member=member)

        try:
            await user.send(text)
            messaging_db.mark_registration_dm_sent(event.id, user.id)
        except discord.Forbidden:
            print(f"Could not DM {user} for event {event.id} registration (DMs closed).")
        except Exception as e:
            print(f"Error sending registration DM: {e}")

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, event: discord.ScheduledEvent, user: discord.User):
        messaging_db.remove_registrant(event.id, user.id)

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        if after.status in (discord.EventStatus.canceled, discord.EventStatus.completed):
            self._cancel_reminder(after.id)
        elif before.start_time != after.start_time:
            # Event got rescheduled -- move the reminder to match, otherwise
            # it fires at the original (now wrong) time.
            self._schedule_reminder(after)

        just_completed = (
            before.status != discord.EventStatus.completed
            and after.status == discord.EventStatus.completed
        )
        if not just_completed or messaging_db.is_followup_scheduled(after.id):
            return

        cfg = messaging_db.get_event_config(after.id)
        delay = cfg.get("followup_delay_minutes")
        if delay is None:
            delay = messaging_db.get_default_followup_delay()

        run_date = datetime.now() + timedelta(minutes=delay)
        self.bot.scheduler.add_job(
            lifecycle_jobs.send_followups_job,
            trigger=DateTrigger(run_date=run_date),
            kwargs={"guild_id": after.guild.id, "event_id": after.id},
            id=f"followup-{after.id}",
        )
        messaging_db.mark_followup_scheduled(after.id)

    # ---- configuration commands ----

    @app_commands.command(
        name="event_message_setup",
        description="Set custom registration/reminder/follow-up messages for one event.",
    )
    @app_commands.describe(
        event="The event to configure",
        registration_message="Custom registration DM. Placeholders: {user_name} {event_name} {event_date} {event_time}",
        reminder_message="Custom pre-event reminder DM. Same placeholders available.",
        reminder_minutes_before="Minutes before the event starts to send the reminder",
        followup_message="Custom follow up DM. Same placeholders available.",
        followup_delay_minutes="Minutes after the event ends to send the follow up (0 = immediately)",
    )
    @app_commands.autocomplete(event=event_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def event_message_setup(
        self,
        interaction: discord.Interaction,
        event: str,
        registration_message: str = None,
        reminder_message: str = None,
        reminder_minutes_before: int = None,
        followup_message: str = None,
        followup_delay_minutes: int = None,
    ):
        event_id = int(event)
        messaging_db.set_event_config(
            event_id, registration_message, followup_message, followup_delay_minutes,
            reminder_message, reminder_minutes_before,
        )
        # If the reminder timing changed, reschedule it immediately rather
        # than waiting for the next event update to pick up the new value.
        if reminder_minutes_before is not None:
            scheduled_event = interaction.guild.get_scheduled_event(event_id)
            if scheduled_event:
                self._schedule_reminder(scheduled_event)
        await interaction.response.send_message(
            "✅ Saved. This event will use the custom values you set (anything left blank still uses the default).",
            ephemeral=True,
        )

    @app_commands.command(
        name="messaging_defaults",
        description="View or update the default registration/reminder/follow-up templates used for all events.",
    )
    @app_commands.describe(
        registration_message="New default registration DM (leave blank to just view current defaults)",
        reminder_message="New default pre-event reminder DM",
        reminder_minutes_before="New default minutes before an event starts to send the reminder",
        followup_message="New default follow up DM",
        followup_delay_minutes="New default delay in minutes after an event ends",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def messaging_defaults(
        self,
        interaction: discord.Interaction,
        registration_message: str = None,
        reminder_message: str = None,
        reminder_minutes_before: int = None,
        followup_message: str = None,
        followup_delay_minutes: int = None,
    ):
        if registration_message:
            messaging_db.set_setting("default_registration_message", registration_message)
        if reminder_message:
            messaging_db.set_setting("default_reminder_message", reminder_message)
        if reminder_minutes_before is not None:
            messaging_db.set_setting("default_reminder_minutes_before", str(reminder_minutes_before))
        if followup_message:
            messaging_db.set_setting("default_followup_message", followup_message)
        if followup_delay_minutes is not None:
            messaging_db.set_setting("default_followup_delay_minutes", str(followup_delay_minutes))

        reg = messaging_db.get_default_registration_message()
        rem = messaging_db.get_default_reminder_message()
        rem_minutes = messaging_db.get_default_reminder_minutes_before()
        fu = messaging_db.get_default_followup_message()
        delay = messaging_db.get_default_followup_delay()
        await interaction.response.send_message(
            f"**Current defaults**\n\n"
            f"Registration DM:\n{reg}\n\n"
            f"Reminder DM (sent {rem_minutes} min before an event starts):\n{rem}\n\n"
            f"Follow up DM (sent {delay} min after an event ends):\n{fu}\n\n"
            f"Placeholders available: `{{user_name}}` `{{event_name}}` `{{event_date}}` `{{event_time}}`",
            ephemeral=True,
        )

    @app_commands.command(
        name="messaging_log_channel",
        description="Set the channel where automated follow up delivery summaries get posted.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def messaging_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        messaging_db.set_setting("log_channel_id", str(channel.id))
        await interaction.response.send_message(
            f"✅ Automated messaging summaries will post in {channel.mention}.", ephemeral=True
        )

    # ---- on-demand bulk send commands ----

    @app_commands.command(
        name="message_event_registrants",
        description="DM everyone who registered interest in a scheduled event, right now.",
    )
    @app_commands.describe(
        event="The event",
        message="Message to send. Leave blank to use that event's registration template.",
    )
    @app_commands.autocomplete(event=event_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message_event_registrants(
        self, interaction: discord.Interaction, event: str, message: str = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
        event_id = int(event)

        scheduled_event = interaction.guild.get_scheduled_event(event_id)
        if scheduled_event is None:
            try:
                scheduled_event = await interaction.guild.fetch_scheduled_event(event_id)
            except Exception:
                scheduled_event = None

        user_ids = messaging_db.get_registrants(event_id)
        if not user_ids and scheduled_event is not None:
            try:
                user_ids = [u.id async for u in scheduled_event.users()]
            except Exception:
                user_ids = []

        if not user_ids:
            await interaction.followup.send("No registrants found for that event.")
            return

        template = message or messaging_db.get_event_config(event_id).get("registration_message") \
            or messaging_db.get_default_registration_message()

        sent, failed = 0, []
        for user_id in user_ids:
            member = interaction.guild.get_member(user_id)
            if member is None:
                continue
            text = render_template(template, event=scheduled_event, member=member)
            try:
                await member.send(text)
                sent += 1
            except Exception:
                failed.append(member.display_name)
            await asyncio.sleep(1)

        result = f"✅ Sent to {sent} member(s)."
        if failed:
            result += f" Could not DM {len(failed)}: {', '.join(failed[:20])}"
        await interaction.followup.send(result)

    @app_commands.command(name="message_role", description="DM everyone who has a specific role.")
    @app_commands.describe(role="The role to message")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message_role(self, interaction: discord.Interaction, role: discord.Role):
        async def on_submit(modal_interaction: discord.Interaction, message: str):
            await modal_interaction.response.defer(thinking=True, ephemeral=True)
            sent, failed = 0, []
            for member in role.members:
                if member.bot:
                    continue
                text = render_template(message, member=member)
                try:
                    await member.send(text)
                    sent += 1
                except Exception:
                    failed.append(member.display_name)
                await asyncio.sleep(1)
            result = f"✅ Sent to {sent} member(s) with **{role.name}**."
            if failed:
                result += f" Could not DM {len(failed)}: {', '.join(failed[:20])}"
            await modal_interaction.followup.send(result)

        await interaction.response.send_modal(
            BulkMessageModal(title=f"Message for @{role.name}", on_submit_callback=on_submit)
        )

    @app_commands.command(
        name="message_missing_role",
        description="DM everyone missing a role (optionally, only among people who have another role).",
    )
    @app_commands.describe(
        role="The role people are missing (e.g. 'Launchpad Complete')",
        must_have_role="Optional: only message people who have this role but are missing the one above (e.g. 'Creator')",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message_missing_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        must_have_role: discord.Role = None,
    ):
        async def on_submit(modal_interaction: discord.Interaction, message: str):
            await modal_interaction.response.defer(thinking=True, ephemeral=True)
            sent, failed = 0, []
            for member in interaction.guild.members:
                if member.bot or role in member.roles:
                    continue
                if must_have_role and must_have_role not in member.roles:
                    continue
                text = render_template(message, member=member)
                try:
                    await member.send(text)
                    sent += 1
                except Exception:
                    failed.append(member.display_name)
                await asyncio.sleep(1)
            result = f"✅ Sent to {sent} member(s) missing **{role.name}**."
            if failed:
                result += f" Could not DM {len(failed)}: {', '.join(failed[:20])}"
            await modal_interaction.followup.send(result)

        title = f"Message for people missing @{role.name}"
        await interaction.response.send_modal(BulkMessageModal(title=title[:45], on_submit_callback=on_submit))


async def setup(bot: commands.Bot):
    messaging_db.init_db()
    await bot.add_cog(LifecycleMessaging(bot))