"""
CLI entry point for the roster extraction script.

Usage:
    roster <video_path> [--output roster.json] [--fps 1]

Or run directly:
    python -m roster_script <video_path>
"""

import argparse
import json
import sys
import os

from roster_script.extractor import extract_frames
from roster_script.ocr import process_frames


def main():
    parser = argparse.ArgumentParser(
        description="Extract alliance roster data from a screen recording.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  roster video.mp4
  roster video.mp4 --output roster.json --fps 2
        """,
    )
    parser.add_argument("video", help="Path to the screen recording (.mp4)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file path (default: roster.json)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=1,
        help="Frames to extract per second (default: 1)",
    )
    parser.add_argument(
        "--frame-dir",
        default=None,
        help="Directory to write extracted frames to (default: a system temp folder)",
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="Keep extracted frame images instead of cleaning up",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print(f"Error: Video file not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or "roster.json"

    # Step 1: Extract frames
    print(f"📹 Extracting frames from {args.video} at {args.fps} fps...")
    frames = extract_frames(args.video, fps=args.fps, output_dir=args.frame_dir)
    print(f"   Extracted {len(frames)} frames.")

    if not frames:
        print("Error: No frames extracted. Check that FFmpeg is installed and the video is valid.", file=sys.stderr)
        sys.exit(1)

    # Step 2: OCR + parse + deduplicate
    print(f"🔍 Running OCR on {len(frames)} frames...")
    roster = process_frames(frames)
    print(f"   Found {len(roster)} unique members.")

    # Step 3: Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2, ensure_ascii=False)

    print(f"✅ Roster saved to {output_path}")

    # Cleanup frames unless --keep-frames
    if not args.keep_frames:
        for frame_path in frames:
            try:
                os.remove(frame_path)
            except OSError:
                pass
        # Try to remove the temp directory
        if frames:
            frame_dir = os.path.dirname(frames[0])
            try:
                os.rmdir(frame_dir)
            except OSError:
                pass


if __name__ == "__main__":
    main()
