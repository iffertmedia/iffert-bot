"""
Wrapper around the OpenAI API for AI-generated content commands
(/voiceover, /accreview, and future ones).

Kept separate from cogs so the API client setup happens once, not per command.
"""

import base64
import os
from openai import AsyncOpenAI

_client = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env file (locally) "
                "or Railway Variables (in production)."
            )
        _client = AsyncOpenAI(api_key=api_key)
    return _client


async def generate(system_prompt: str, user_message: str) -> str:
    """Single-turn chat completion. Returns the raw text response."""
    client = get_client()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.9,  # higher temp helps satisfy "rotate phrasing, never reuse lines"
        max_tokens=900,
    )
    return response.choices[0].message.content


async def transcribe_audio(file_path: str) -> str:
    """
    Transcribes an audio file via OpenAI's Whisper endpoint.
    Note: the endpoint caps uploads at 25MB, which is why /accreview extracts
    a compressed audio-only track from the video rather than uploading the
    whole (possibly 100MB) video file.
    """
    client = get_client()
    with open(file_path, "rb") as f:
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return transcript.text


async def generate_with_images(system_prompt: str, user_message: str, image_paths: list[str]) -> str:
    """Chat completion with image inputs, for vision-based review tasks like /accreview."""
    client = get_client()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    content = [{"type": "text", "text": user_message}]
    for path in image_paths:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        temperature=0.9,
        max_tokens=1200,
    )
    return response.choices[0].message.content

