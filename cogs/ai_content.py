import discord
from discord import app_commands
from discord.ext import commands

import ai_client
from prompts import VOICEOVER_SYSTEM_PROMPT

TIER_CHOICES = [
    app_commands.Choice(name="Convenience", value="convenience"),
    app_commands.Choice(name="Budget", value="budget"),
    app_commands.Choice(name="Standard", value="standard"),
    app_commands.Choice(name="Luxury", value="luxury"),
    app_commands.Choice(name="Resort", value="resort"),
]

LEVEL_CHOICES = [
    app_commands.Choice(name="L0", value="L0"),
    app_commands.Choice(name="L1", value="L1"),
    app_commands.Choice(name="L2", value="L2"),
    app_commands.Choice(name="L3", value="L3"),
    app_commands.Choice(name="L4", value="L4"),
]

DISCORD_MESSAGE_LIMIT = 1900  # a little under Discord's 2000 char cap, for safety


def chunk_text(text: str, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """Split text into Discord-safe chunks, breaking on blank lines where possible."""
    if len(text) <= limit:
        return [text]

    chunks = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            # paragraph itself might exceed the limit; hard-split if so
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


class AIContent(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="voiceover",
        description="Generate a TikTok GO voiceover script + filming tips for a property.",
    )
    @app_commands.describe(
        property_name="Property name exactly as it shows on TikTok GO / Google Maps",
        tier="Property tier",
        creator_level="Creator's level (affects script tone)",
    )
    @app_commands.choices(tier=TIER_CHOICES, creator_level=LEVEL_CHOICES)
    async def voiceover(
        self,
        interaction: discord.Interaction,
        property_name: str,
        tier: app_commands.Choice[str],
        creator_level: app_commands.Choice[str],
    ):
        # Generation can take a few seconds, so defer to avoid Discord's 3s timeout.
        await interaction.response.defer(thinking=True)

        user_message = (
            f"Property name: {property_name}\n"
            f"Property tier: {tier.value}\n"
            f"Creator Level: {creator_level.value}"
        )

        try:
            result = await ai_client.generate(VOICEOVER_SYSTEM_PROMPT, user_message)
        except RuntimeError as e:
            await interaction.followup.send(f"⚠️ {e}")
            return
        except Exception as e:
            await interaction.followup.send(f"⚠️ Generation failed: {e}")
            return

        header = f"**🎬 Voiceover script — {property_name}** ({tier.name} · {creator_level.name})\n\n"
        full_text = header + result

        chunks = chunk_text(full_text)
        await interaction.followup.send(chunks[0])
        for chunk in chunks[1:]:
            await interaction.channel.send(chunk)


async def setup(bot: commands.Bot):
    await bot.add_cog(AIContent(bot))
