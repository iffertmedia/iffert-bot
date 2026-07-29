import asyncio
import io

import discord
from discord import app_commands
from discord.ext import commands

from cover_generator import generate_cover

STYLE_CHOICES = [
    app_commands.Choice(name="Bold", value="bold"),
    app_commands.Choice(name="Clean", value="clean"),
    app_commands.Choice(name="Luxury", value="luxury"),
    app_commands.Choice(name="Fun", value="fun"),
    app_commands.Choice(name="Food-focused", value="food"),
    app_commands.Choice(name="Travel-focused", value="travel"),
    app_commands.Choice(name="Dramatic", value="dramatic"),
]

MAX_HEADLINE_LEN = 90  # keeps even worst-case wrapping readable at min font size


class Cover(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="cover",
        description="Generate a TikTok cover image from an uploaded photo + headline.",
    )
    @app_commands.describe(
        image="A clear vertical photo to use as the cover's main image",
        headline="The exact cover headline (used exactly as typed, not rewritten)",
        category="Content category (e.g. hotel, food, travel)",
        style="Visual style",
    )
    @app_commands.choices(style=STYLE_CHOICES)
    async def cover(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        headline: str,
        category: str,
        style: app_commands.Choice[str],
    ):
        if not (image.content_type or "").startswith("image/"):
            await interaction.response.send_message(
                "⚠️ That file doesn't look like an image. Please upload a clear vertical photo (JPG or PNG).",
                ephemeral=True,
            )
            return

        if len(headline) > MAX_HEADLINE_LEN:
            await interaction.response.send_message(
                f"⚠️ Headline is too long ({len(headline)} chars). Keep it under {MAX_HEADLINE_LEN} "
                "characters so it stays readable on the cover.",
                ephemeral=True,
            )
            return

        # Image processing takes a moment, so defer to avoid Discord's 3s timeout.
        await interaction.response.defer(thinking=True)

        try:
            photo_bytes = await image.read()
        except Exception as e:
            await interaction.followup.send(f"⚠️ Couldn't download the uploaded image: {e}")
            return

        try:
            # Pillow work is CPU-bound and blocking; run off the event loop.
            loop = asyncio.get_running_loop()
            cover_bytes = await loop.run_in_executor(
                None, generate_cover, photo_bytes, headline, style.value
            )
        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Couldn't generate the cover: {e}\n"
                "This usually means the uploaded file wasn't a readable image."
            )
            return

        file = discord.File(io.BytesIO(cover_bytes), filename="cover.png")
        await interaction.followup.send(
            content=f"**🖼️ Cover — {category}** ({style.name})\nHeadline: \"{headline}\"",
            file=file,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Cover(bot))
