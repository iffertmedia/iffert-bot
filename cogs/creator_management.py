import calendar

import discord
from discord import app_commands
from discord.ext import commands
from apscheduler.triggers.cron import CronTrigger

import creator_db
import creator_jobs
from creator_jobs import render

LEVEL_CHOICES = [app_commands.Choice(name=lvl, value=lvl) for lvl in creator_db.LEVELS]


class CreatorManagement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        creator_jobs.set_bot(bot)

    async def cog_load(self):
        # Registered once with a fixed id + replace_existing so restarts
        # don't create duplicate daily jobs; persists via the same disk
        # backed scheduler as /schedule and the lifecycle messaging follow ups.
        self.bot.scheduler.add_job(
            creator_jobs.daily_birthday_check,
            trigger=CronTrigger(hour=9, minute=0),
            id="daily-birthday-check",
            replace_existing=True,
        )

    # ---- welcome message ----

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        text = render(creator_db.get_default_welcome_dm(), member=member)
        try:
            await member.send(text)
        except discord.Forbidden:
            print(f"Could not DM welcome message to {member} (DMs closed).")
        except Exception as e:
            print(f"Error sending welcome DM: {e}")

    # ---- level management ----

    @app_commands.command(
        name="level",
        description="Set a creator's level: assigns the role, announces it, and DMs them.",
    )
    @app_commands.describe(member="The creator", level="Their new level")
    @app_commands.choices(level=LEVEL_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def level(
        self, interaction: discord.Interaction, member: discord.Member, level: app_commands.Choice[str]
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        target_role_id = creator_db.get_level_role_id(level.value)
        if not target_role_id:
            await interaction.followup.send(
                f"⚠️ No Discord role is mapped to {level.value} yet. Run `/set_level_role` first."
            )
            return

        target_role = interaction.guild.get_role(target_role_id)
        if not target_role:
            await interaction.followup.send(
                f"⚠️ The role mapped to {level.value} no longer exists. Run `/set_level_role` to fix it."
            )
            return

        all_level_role_ids = {rid for rid in creator_db.get_all_level_role_ids().values() if rid}
        roles_to_remove = [r for r in member.roles if r.id in all_level_role_ids and r.id != target_role_id]

        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Level updated")
            if target_role not in member.roles:
                await member.add_roles(target_role, reason="Level updated")
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to manage that role. In Server Settings → Roles, "
                "make sure my bot's role is positioned above it."
            )
            return

        dm_sent = True
        try:
            await member.send(render(creator_db.get_default_level_dm(), member=member, level=level.value))
        except Exception:
            dm_sent = False

        channel_id = creator_db.get_channel_setting("level_announce")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                await channel.send(render(creator_db.get_default_level_announce(), member=member, level=level.value))

        result = f"✅ {member.display_name} is now {level.value}."
        if not dm_sent:
            result += " (Could not DM them — they may have DMs disabled.)"
        await interaction.followup.send(result)

    # ---- launchpad certification ----

    @app_commands.command(
        name="certify",
        description="Certify a Launchpad member: adds GO Creator, removes their cohort role.",
    )
    @app_commands.describe(member="The creator")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def certify(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(thinking=True, ephemeral=True)

        go_creator_role_id = creator_db.get_level_role_id("GO Creator")
        if not go_creator_role_id:
            await interaction.followup.send(
                "⚠️ The GO Creator level role isn't configured yet. Run "
                "`/set_level_role level:\"GO Creator\"` first."
            )
            return

        go_creator_role = interaction.guild.get_role(go_creator_role_id)
        if not go_creator_role:
            await interaction.followup.send(
                "⚠️ The configured GO Creator role no longer exists on this server. "
                "Re-run `/set_level_role` to fix it."
            )
            return

        roles_to_add = [go_creator_role] if go_creator_role not in member.roles else []

        cohort_role_ids = {rid for rid in creator_db.get_all_cohort_role_ids().values() if rid}
        roles_to_remove = [r for r in member.roles if r.id in cohort_role_ids]

        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Certified Launchpad completion")
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Certified — leaving Launchpad cohort")
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to manage those roles. In Server Settings → Roles, "
                "make sure my bot's role is positioned above GO Creator and the cohort roles."
            )
            return

        dm_sent = True
        try:
            await member.send(render(creator_db.get_default_certify_dm(), member=member))
        except Exception:
            dm_sent = False

        channel_id = creator_db.get_channel_setting("certify_announce")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                await channel.send(render(creator_db.get_default_certify_announce(), member=member))

        result = f"✅ {member.display_name} is certified — added GO Creator"
        if roles_to_remove:
            result += f", removed {', '.join(r.name for r in roles_to_remove)}"
        result += "."
        if not dm_sent:
            result += " (Could not DM them — they may have DMs disabled.)"
        await interaction.followup.send(result)

    # ---- birthdays (self service) ----

    @app_commands.command(name="set_birthday", description="Set your birthday for team shoutouts (no year needed).")
    @app_commands.describe(month="Month (1-12)", day="Day (1-31)")
    async def set_birthday(
        self,
        interaction: discord.Interaction,
        month: app_commands.Range[int, 1, 12],
        day: app_commands.Range[int, 1, 31],
    ):
        max_day = calendar.monthrange(2024, month)[1]  # 2024 is a leap year, so Feb 29 is accepted
        if day > max_day:
            await interaction.response.send_message(
                f"⚠️ {calendar.month_name[month]} doesn't have {day} days.", ephemeral=True
            )
            return
        creator_db.set_birthday(interaction.user.id, month, day)
        await interaction.response.send_message(
            f"✅ Got it — your birthday is set to {calendar.month_name[month]} {day}.", ephemeral=True
        )

    @app_commands.command(name="my_birthday", description="Check the birthday you have on file.")
    async def my_birthday(self, interaction: discord.Interaction):
        bday = creator_db.get_birthday(interaction.user.id)
        if not bday:
            await interaction.response.send_message(
                "You haven't set a birthday yet — use `/set_birthday` to add one.", ephemeral=True
            )
            return
        month, day = bday
        await interaction.response.send_message(
            f"Your birthday on file: {calendar.month_name[month]} {day}.", ephemeral=True
        )

    # ---- setup / configuration commands ----

    @app_commands.command(name="set_level_role", description="Map a creator level to a Discord role.")
    @app_commands.choices(level=LEVEL_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_level_role(
        self, interaction: discord.Interaction, level: app_commands.Choice[str], role: discord.Role
    ):
        creator_db.set_level_role_id(level.value, role.id)
        await interaction.response.send_message(f"✅ {level.value} is now mapped to {role.mention}.", ephemeral=True)


    @app_commands.command(
        name="set_launchpad_cohort_role",
        description="Map a Launchpad cohort (Green/Purple/Red) to its Discord role.",
    )
    @app_commands.choices(cohort=[app_commands.Choice(name=c, value=c) for c in creator_db.COHORTS])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_launchpad_cohort_role(
        self, interaction: discord.Interaction, cohort: app_commands.Choice[str], role: discord.Role
    ):
        creator_db.set_cohort_role_id(cohort.value, role.id)
        await interaction.response.send_message(
            f"✅ Launchpad {cohort.value} is now mapped to {role.mention}.", ephemeral=True
        )

    @app_commands.command(name="level_announce_channel", description="Set the channel for level-up announcements.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def level_announce_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        creator_db.set_channel_setting("level_announce", channel.id)
        await interaction.response.send_message(
            f"✅ Level-up announcements will post in {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="certify_announce_channel", description="Set the channel for Launchpad completion announcements.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def certify_announce_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        creator_db.set_channel_setting("certify_announce", channel.id)
        await interaction.response.send_message(
            f"✅ Launchpad completion announcements will post in {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="birthday_announce_channel", description="Set the channel for birthday shoutouts.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def birthday_announce_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        creator_db.set_channel_setting("birthday_announce", channel.id)
        await interaction.response.send_message(
            f"✅ Birthday shoutouts will post in {channel.mention}.", ephemeral=True
        )

    @app_commands.command(
        name="creator_message_defaults",
        description="View or update the welcome/level/certify/birthday message templates.",
    )
    @app_commands.describe(
        welcome_dm="New welcome DM template",
        level_dm="New level up DM template",
        level_announce="New level up channel announcement template",
        certify_dm="New Launchpad completion DM template",
        certify_announce="New Launchpad completion channel announcement template",
        birthday_announce="New birthday channel announcement template",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def creator_message_defaults(
        self,
        interaction: discord.Interaction,
        welcome_dm: str = None,
        level_dm: str = None,
        level_announce: str = None,
        certify_dm: str = None,
        certify_announce: str = None,
        birthday_announce: str = None,
    ):
        if welcome_dm:
            creator_db.set_setting("welcome_dm_template", welcome_dm)
        if level_dm:
            creator_db.set_setting("level_dm_template", level_dm)
        if level_announce:
            creator_db.set_setting("level_announce_template", level_announce)
        if certify_dm:
            creator_db.set_setting("certify_dm_template", certify_dm)
        if certify_announce:
            creator_db.set_setting("certify_announce_template", certify_announce)
        if birthday_announce:
            creator_db.set_setting("birthday_announce_template", birthday_announce)

        await interaction.response.send_message(
            f"**Welcome DM:**\n{creator_db.get_default_welcome_dm()}\n\n"
            f"**Level up DM:**\n{creator_db.get_default_level_dm()}\n\n"
            f"**Level up announcement:**\n{creator_db.get_default_level_announce()}\n\n"
            f"**Launchpad DM:**\n{creator_db.get_default_certify_dm()}\n\n"
            f"**Launchpad announcement:**\n{creator_db.get_default_certify_announce()}\n\n"
            f"**Birthday announcement:**\n{creator_db.get_default_birthday_announce()}\n\n"
            f"Placeholders: `{{user_name}}` and `{{level}}` (level up messages only).",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    creator_db.init_db()
    await bot.add_cog(CreatorManagement(bot))
