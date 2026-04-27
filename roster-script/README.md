# Kingshot Roster Extraction Script

A standalone CLI tool that extracts alliance roster data from screen recordings of the Kingshot alliance member list. It uses FFmpeg for frame extraction and Tesseract OCR for text recognition.

## Prerequisites

Install these system dependencies:

### Windows
- **FFmpeg**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
- **Tesseract-OCR**: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH

Or install both with Scoop:

```bash
scoop install ffmpeg tesseract
```

### Linux (Debian/Ubuntu)
```bash
sudo apt-get install ffmpeg tesseract-ocr tesseract-ocr-eng
```

### macOS
```bash
brew install ffmpeg tesseract
```

## Installation

```bash
cd roster-script
uv sync
```

## Usage

```bash
# Basic usage
uv run roster video.mp4

# Specify output file
uv run roster video.mp4 --output roster.json

# Extract more frames per second for fast-scrolling videos
uv run roster video.mp4 --fps 2

# Write frames to a local temp directory instead of the system temp folder
uv run roster video.mp4 --frame-dir ./.roster_frames

# Keep extracted frame images for debugging
uv run roster video.mp4 --keep-frames
```

## Output Format

The script outputs a JSON array suitable for `/upload_roster`.
Alliance is now selected in the slash command, so each JSON row only needs
`ign` and `rank` for bot reconciliation.

```json
[
  {"ign": "DarkLord99", "rank": "R4"},
  {"ign": "ShadowKnight", "rank": "R3"},
  {"ign": "NovaStrike", "rank": "R2"}
]
```

## Workflow

1. Record a screen capture of scrolling through the alliance member list in Kingshot
2. Run this script on the recording
3. Review the output JSON for any OCR errors
4. Upload the JSON file using `/upload_roster` and select alliance in the command
5. The bot will automatically process it and sync roles
