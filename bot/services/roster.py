import json
import logging
from datetime import datetime, timezone
import aiohttp
from services.database import bulk_update_roster, mark_absent
from services.role_sync import sync_all_users

logger = logging.getLogger(__name__)

VALID_ALLIANCES = {"BOO", "ZEN"}
VALID_RANKS = {"R1", "R2", "R3", "R4", "R5"}

def validate_roster_json(data: list | dict | str) -> None:
    """Validate the structure of a roster JSON payload."""
    if not isinstance(data, list):
        raise ValueError("JSON must be an array of objects.")

    if len(data) == 0:
        raise ValueError("JSON array is empty.")

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {i} is not an object.")
        if "ign" not in entry:
            raise ValueError(f"Entry {i} is missing 'ign' field.")
        if not isinstance(entry["ign"], str) or not entry["ign"].strip():
            raise ValueError(f"Entry {i} has invalid 'ign' (must be non-empty string).")

        rank = entry.get("rank")
        if rank and rank not in VALID_RANKS:
            raise ValueError(f"Entry {i} has invalid rank '{rank}'. Must be one of {VALID_RANKS}.")

import discord

async def fetch_roster_attachment(attachment: discord.Attachment) -> list[dict] | None:
    try:
        raw = await attachment.read()
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to decode attachment: {e}")
        return None

async def process_roster(guild: discord.Guild, data: list[dict], alliance: str) -> dict[str, int | dict]:
    timestamp = datetime.now(timezone.utc)
    bulk_update_roster(data, alliance, timestamp)
    removed_count = mark_absent(alliance, timestamp)
    sync_summary = await sync_all_users(guild)
    return {
        "processed": len(data),
        "removed": removed_count,
        "sync_summary": sync_summary
    }
