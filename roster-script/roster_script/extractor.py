"""
extractor.py – Extract frames from a video file using FFmpeg.
"""

import subprocess
import tempfile
import os
import sys


def extract_frames(video_path: str, fps: int = 1, output_dir: str | None = None) -> list[str]:
    """
    Extract frames from a video at the given FPS rate using FFmpeg.

    Args:
        video_path: Path to the input video file.
        fps: Number of frames to extract per second.
        output_dir: Directory to save frames to. If None, uses a temp directory.

    Returns:
        List of absolute paths to extracted frame images (PNG).
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="roster_frames_")
    else:
        os.makedirs(output_dir, exist_ok=True)

    output_pattern = os.path.join(output_dir, "frame_%04d.png")

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",          # High quality
        output_pattern,
        "-y",                  # Overwrite existing
        "-loglevel", "error",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        print(
            "Error: FFmpeg not found. Please install FFmpeg and ensure it is on your PATH.",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: FFmpeg failed:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)

    # Collect extracted frame paths in sorted order
    frames = sorted(
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.startswith("frame_") and f.endswith(".png")
    )

    return frames
