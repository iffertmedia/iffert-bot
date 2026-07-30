import os
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from dotenv import load_dotenv

import jobs

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # optional: set for instant command sync in one server during dev

intents = discord.Intents.default()
intents.members = True  # needed later for role assignment / welcome messages

os.makedirs("data", exist_ok=True)


class IffertBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        # SQLAlchemyJobStore persists scheduled jobs to disk, so recurring
        # posts survive a bot restart or redeploy instead of silently vanishing.
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": SQLAlchemyJobStore(url="sqlite:///data/schedule.db")},
            timezone=os.getenv("BOT_TIMEZONE", "America/Chicago"),
        )

    async def setup_hook(self):
        jobs.set_bot(self)

        await self.load_extension("cogs.general")
        await self.load_extension("cogs.scheduler")
        await self.load_extension("cogs.ai_content")
        await self.load_extension("cogs.cover")
        await self.load_extension("cogs.accreview")

        self.scheduler.start()

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
        else:
            synced = await self.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")


bot = IffertBot()

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit(
            "DISCORD_TOKEN not set. Copy .env.example to .env and fill in your bot token."
        )
    bot.run(TOKEN)
