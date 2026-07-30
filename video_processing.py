"""
Extracts frames and audio from an uploaded video for /accreview.

Uses ffmpeg directly (bundled via imageio-ffmpeg, so no system package install
is needed on Railway) rather than any AI video-understanding service -- frame
extraction and audio extraction are fully deterministic and free.
"""

import os
import re
import subprocess
import tempfile

import imageio_ffmpeg

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()

FRAME_FRACTIONS = (0.02, 0.25, 0.50, 0.75, 0.95)  # sample points across the video
FRAME_WIDTH = 768  # keep vision API payload small; more than enough detail to judge shots


class VideoProcessingError(Exception):
    pass


def _run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def get_duration_seconds(video_path: str) -> float:
    """Parses duration from ffmpeg's stderr output (no separate ffprobe binary needed)."""
    result = _run([FFMPEG_BIN, "-i", video_path])
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        raise VideoProcessingError(
            "Couldn't read video duration. The file may be corrupted or not a "
            "readable video format."
        )
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def extract_frames(video_path: str, out_dir: str) -> list[str]:
    """Extracts frames at fixed fractional points across the video. Returns file paths."""
    duration = get_duration_seconds(video_path)
    frame_paths = []

    for i, fraction in enumerate(FRAME_FRACTIONS):
        timestamp = max(0.1, duration * fraction)
        out_path = os.path.join(out_dir, f"frame_{i}.jpg")
        cmd = [
            FFMPEG_BIN, "-y", "-ss", f"{timestamp:.2f}", "-i", video_path,
            "-frames:v", "1", "-q:v", "3",
            "-vf", f"scale={FRAME_WIDTH}:-1",
            out_path,
        ]
        result = _run(cmd)
        if os.path.isfile(out_path):
            frame_paths.append(out_path)
        else:
            print(f"Frame extraction failed at {timestamp:.2f}s: {result.stderr[-300:]}")

    if not frame_paths:
        raise VideoProcessingError(
            "Couldn't extract any frames from this video. The file may be corrupted."
        )
    return frame_paths


def extract_audio(video_path: str, out_dir: str) -> str | None:
    """
    Extracts a compressed mono audio track for transcription.
    Returns None if the video has no audio stream (silent video).
    """
    out_path = os.path.join(out_dir, "audio.mp3")
    cmd = [
        FFMPEG_BIN, "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k",
        out_path,
    ]
    result = _run(cmd)
    if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    return None
