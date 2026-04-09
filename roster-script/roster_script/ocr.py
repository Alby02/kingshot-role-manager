"""
ocr.py – Tesseract OCR processing, regex parsing, and fuzzy deduplication
for alliance roster frames.
"""

import re
import pytesseract
from PIL import Image
from thefuzz import fuzz


# Rank headers as they appear in Kingshot alliance roster screens
RANK_PATTERN = re.compile(r"\b(R[1-5])\b", re.IGNORECASE)

# Minimum fuzzy match ratio to consider two IGNs as the same player
FUZZY_THRESHOLD = 85

# Minimum IGN length to accept (filters OCR noise)
MIN_IGN_LENGTH = 2


def ocr_frame(frame_path: str) -> str:
    """Run Tesseract OCR on a single frame image and return the raw text."""
    try:
        image = Image.open(frame_path)
        text = pytesseract.image_to_string(image, lang="eng")
        return text
    except Exception as e:
        print(f"  Warning: OCR failed on {frame_path}: {e}")
        return ""


def parse_roster_text(text: str) -> list[dict]:
    """
    Parse OCR text output to extract player names and their ranks.

    The Kingshot alliance roster screen shows rank headers (R5, R4, R3, R2, R1)
    followed by lists of player names under each rank section.

    Returns a list of dicts: [{"ign": "...", "rank": "R4"}, ...]
    """
    entries = []
    current_rank = None
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this line is a rank header
        rank_match = RANK_PATTERN.search(line)
        if rank_match:
            current_rank = rank_match.group(1).upper()
            # If the line is ONLY the rank header, skip to next line
            remaining = RANK_PATTERN.sub("", line).strip()
            if not remaining or len(remaining) < MIN_IGN_LENGTH:
                continue
            # Otherwise the rank + name might be on same line
            line = remaining

        if current_rank and len(line) >= MIN_IGN_LENGTH:
            # Clean up common OCR artifacts
            cleaned = clean_ign(line)
            if cleaned and len(cleaned) >= MIN_IGN_LENGTH:
                entries.append({"ign": cleaned, "rank": current_rank})

    return entries


def clean_ign(text: str) -> str:
    """Clean up common OCR artifacts from an IGN."""
    # Remove leading/trailing special characters that are likely OCR noise
    cleaned = re.sub(r'^[^a-zA-Z0-9]+', '', text)
    cleaned = re.sub(r'[^a-zA-Z0-9_\-. ]+$', '', cleaned)
    cleaned = cleaned.strip()
    return cleaned


def deduplicate(entries: list[dict]) -> list[dict]:
    """
    Deduplicate roster entries using fuzzy string matching.

    When the same player appears across multiple frames (due to scrolling),
    we keep the first occurrence and merge duplicates.
    """
    unique = []

    for entry in entries:
        is_duplicate = False
        for existing in unique:
            ratio = fuzz.ratio(entry["ign"].lower(), existing["ign"].lower())
            if ratio >= FUZZY_THRESHOLD:
                is_duplicate = True
                # Keep the longer IGN (more likely to be correct)
                if len(entry["ign"]) > len(existing["ign"]):
                    existing["ign"] = entry["ign"]
                # Keep rank if we didn't have one
                if not existing.get("rank") and entry.get("rank"):
                    existing["rank"] = entry["rank"]
                break

        if not is_duplicate:
            unique.append(entry)

    return unique


def process_frames(frame_paths: list[str], alliance: str) -> list[dict]:
    """
    Full pipeline: OCR all frames → parse → deduplicate → attach alliance tag.

    Args:
        frame_paths: List of paths to frame images.
        alliance: Alliance tag to attach (e.g., "BOO", "ZEN").

    Returns:
        Deduplicated roster: [{"ign": "...", "rank": "R4", "alliance": "BOO"}, ...]
    """
    all_entries = []

    for i, frame_path in enumerate(frame_paths):
        text = ocr_frame(frame_path)
        entries = parse_roster_text(text)
        all_entries.extend(entries)

        # Progress indicator
        if (i + 1) % 10 == 0 or i == len(frame_paths) - 1:
            print(f"   Processed {i + 1}/{len(frame_paths)} frames ({len(all_entries)} raw entries)")

    # Deduplicate across all frames
    unique = deduplicate(all_entries)

    # Attach alliance tag
    for entry in unique:
        entry["alliance"] = alliance

    return unique
