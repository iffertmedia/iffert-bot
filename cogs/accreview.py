import asyncio
import os
import tempfile

import discord
from discord import app_commands
from discord.ext import commands

import ai_client
import video_processing
from video_processing import VideoProcessingError
from prompts import ACCREVIEW_SYSTEM_PROMPT

MAX_VIDEO_BYTES = 100 * 1024 * 1024  # 100MB, matches the server's Nitro boost upload limit
DISCORD_MESSAGE_LIMIT = 1900

MODE_CHOICES = [
    app_commands.Choice(name="Voiceover (transcribe spoken audio)", value="voiceover"),
    app_commands.Choice(name="Text only (I'll type my script/captions)", value="text"),
]

LEVEL_CHOICES = [
    app_commands.Choice(name="L0", value="L0"),
    app_commands.Choice(name="L1", value="L1"),
    app_commands.Choice(name="L2", value="L2"),
    app_commands.Choice(name="L3", value="L3"),
    app_commands.Choice(name="L4", value="L4"),
    app_commands.Choice(name="L5", value="L5"),
]


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


def _process_video_sync(video_path: str, need_audio: bool) -> tuple[list[str], str | None]:
    """Runs in a thread executor since ffmpeg subprocess calls are blocking."""
    tmp_dir = os.path.dirname(video_path)
    frames = video_processing.extract_frames(video_path, tmp_dir)
    audio_path = video_processing.extract_audio(video_path, tmp_dir) if need_audio else None
    return frames, audio_path


class AccReview(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="accreview",
        description="Get AI feedback on an accommodation (ACC) video against the Hotel Advisor framework.",
    )
    @app_commands.describe(
        video="The video to review (up to 100MB)",
        mode="Grade from spoken voiceover audio, or from text you type yourself",
        creator_level="Your creator level (affects how strictly the script is graded)",
        script_text="Required if mode is 'Text only': paste your script or on-screen text",
        property_name="Optional: hotel/property name for context",
    )
    @app_commands.choices(mode=MODE_CHOICES, creator_level=LEVEL_CHOICES)
    async def accreview(
        self,
        interaction: discord.Interaction,
        video: discord.Attachment,
        mode: app_commands.Choice[str],
        creator_level: app_commands.Choice[str],
        script_text: str = None,
        property_name: str = None,
    ):
        if not (video.content_type or "").startswith("video/"):
            await interaction.response.send_message(
                "⚠️ That file doesn't look like a video. Please upload an mp4 or mov file.",
                ephemeral=True,
            )
            return

        if video.size > MAX_VIDEO_BYTES:
            mb = video.size / (1024 * 1024)
            await interaction.response.send_message(
                f"⚠️ That file is {mb:.0f}MB, which is over the 100MB limit. Try a smaller export.",
                ephemeral=True,
            )
            return

        if mode.value == "text" and not script_text:
            await interaction.response.send_message(
                "⚠️ Text mode needs the `script_text` field filled in with your script or on-screen text.",
                ephemeral=True,
            )
            return

        # Video download + ffmpeg processing + transcription + vision call can
        # take a while, so defer immediately to avoid Discord's 3s timeout.
        await interaction.response.defer(thinking=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            video_path = os.path.join(tmp_dir, "input_video")
            try:
                video_bytes = await video.read()
                with open(video_path, "wb") as f:
                    f.write(video_bytes)
            except Exception as e:
                await interaction.followup.send(f"⚠️ Couldn't download the uploaded video: {e}")
                return

            need_audio = mode.value == "voiceover"
            try:
                loop = asyncio.get_running_loop()
                frames, audio_path = await loop.run_in_executor(
                    None, _process_video_sync, video_path, need_audio
                )
            except VideoProcessingError as e:
                await interaction.followup.send(f"⚠️ {e}")
                return
            except Exception as e:
                await interaction.followup.send(f"⚠️ Couldn't process the video: {e}")
                return

            transcript_or_text = script_text
            if mode.value == "voiceover":
                if audio_path is None:
                    await interaction.followup.send(
                        "⚠️ This video doesn't seem to have an audio track. "
                        "If it's a text-overlay-only video, try again with mode set to 'Text only'."
                    )
                    return
                try:
                    transcript_or_text = await ai_client.transcribe_audio(audio_path)
                except Exception as e:
                    await interaction.followup.send(f"⚠️ Transcription failed: {e}")
                    return

            context_lines = [f"Creator level: {creator_level.value}"]
            if property_name:
                context_lines.append(f"Property: {property_name}")
            context_lines.append(
                f"Script source: {'transcribed voiceover audio' if mode.value == 'voiceover' else 'creator-provided text'}"
            )
            context_lines.append(f"Transcript/script:\n{transcript_or_text}")
            user_message = "\n".join(context_lines)

            try:
                review = await ai_client.generate_with_images(
                    ACCREVIEW_SYSTEM_PROMPT, user_message, frames
                )
            except Exception as e:
                await interaction.followup.send(f"⚠️ Review generation failed: {e}")
                return

        header_bits = [f"🎬 **ACC Review** — {creator_level.name}"]
        if property_name:
            header_bits.append(property_name)
        header = " · ".join(header_bits) + "\n\n"
        full_text = header + review

        chunks = chunk_text(full_text)
        await interaction.followup.send(chunks[0])
        for chunk in chunks[1:]:
            await interaction.channel.send(chunk)


async def setup(bot: commands.Bot):
    await bot.add_cog(AccReview(bot))
