import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

import analytics_db

METRIC_CHOICES = [
    app_commands.Choice(name="Messages", value="messages"),
    app_commands.Choice(name="Reactions given", value="reactions_given"),
    app_commands.Choice(name="Voice/Stage time", value="voice_seconds"),
]


def _today_iso() -> str:
    tz_name = os.getenv("BOT_TIMEZONE", "America/Chicago")
    return datetime.now(ZoneInfo(tz_name)).date().isoformat()


def _now_iso() -> str:
    tz_name = os.getenv("BOT_TIMEZONE", "America/Chicago")
    return datetime.now(ZoneInfo(tz_name)).isoformat()


def _date_range(days: int) -> tuple:
    tz_name = os.getenv("BOT_TIMEZONE", "America/Chicago")
    today = datetime.now(ZoneInfo(tz_name)).date()
    start = today - timedelta(days=days - 1)
    return start.isoformat(), today.isoformat()


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


class Analytics(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---- tracking listeners ----

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        analytics_db.record_message(message.author.id, _today_iso())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return
        member = payload.member
        if member is not None and member.bot:
            return
        analytics_db.record_reaction(payload.user_id, _today_iso())

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if member.bot:
            return

        before_channel = before.channel
        after_channel = after.channel

        if before_channel is None and after_channel is not None:
            # joined a voice/stage channel from being disconnected
            analytics_db.start_voice_session(member.id, after_channel.id, _now_iso())
            analytics_db.record_voice_join(member.id, _today_iso())

        elif before_channel is not None and after_channel is None:
            # left voice entirely -- close out the session and log the duration
            self._close_session(member.id)

        elif before_channel is not None and after_channel is not None and before_channel.id != after_channel.id:
            # switched channels without fully disconnecting -- close old session, start a new one
            self._close_session(member.id)
            analytics_db.start_voice_session(member.id, after_channel.id, _now_iso())
            analytics_db.record_voice_join(member.id, _today_iso())

    def _close_session(self, user_id: int):
        session = analytics_db.get_voice_session(user_id)
        if session is None:
            return
        try:
            joined_at = datetime.fromisoformat(session["joined_at"])
            now = datetime.fromisoformat(_now_iso())
            elapsed_seconds = max(0, int((now - joined_at).total_seconds()))
        except Exception as e:
            print(f"Failed to compute voice session duration: {e}")
            elapsed_seconds = 0
        analytics_db.record_voice_time(user_id, _today_iso(), elapsed_seconds)
        analytics_db.end_voice_session(user_id)

    # ---- reports ----

    @app_commands.command(name="activity_report", description="See engagement stats for yourself or another member.")
    @app_commands.describe(member="Leave blank to see your own stats", days="Number of days back to include (default 30)")
    async def activity_report(
        self, interaction: discord.Interaction, member: discord.Member = None, days: app_commands.Range[int, 1, 365] = 30
    ):
        target = member or interaction.user
        start, end = _date_range(days)
        totals = analytics_db.get_totals_for_user(target.id, start, end)

        who = "Your" if target == interaction.user else f"{target.display_name}'s"
        await interaction.response.send_message(
            f"**{who} activity — last {days} days**\n\n"
            f"Messages: {totals['messages']}\n"
            f"Reactions given: {totals['reactions_given']}\n"
            f"Voice/Stage time: {_format_duration(totals['voice_seconds'])} "
            f"({totals['voice_joins']} join{'s' if totals['voice_joins'] != 1 else ''})",
            ephemeral=True,
        )

    @app_commands.command(name="activity_leaderboard", description="See the most engaged members over a time period.")
    @app_commands.describe(metric="What to rank by", days="Number of days back to include (default 30)")
    @app_commands.choices(metric=METRIC_CHOICES)
    async def activity_leaderboard(
        self, interaction: discord.Interaction, metric: app_commands.Choice[str],
        days: app_commands.Range[int, 1, 365] = 30
    ):
        start, end = _date_range(days)
        top = analytics_db.get_leaderboard(metric.value, start, end, limit=10)

        if not top:
            await interaction.response.send_message("No activity recorded in that period yet.", ephemeral=True)
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (user_id, total) in enumerate(top):
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            prefix = medals[i] if i < 3 else f"{i + 1}."
            value = _format_duration(total) if metric.value == "voice_seconds" else str(total)
            lines.append(f"{prefix} {name} — {value}")

        await interaction.response.send_message(
            f"**📊 {metric.name} — last {days} days**\n" + "\n".join(lines)
        )


async def setup(bot: commands.Bot):
    analytics_db.init_db()
    await bot.add_cog(Analytics(bot))
