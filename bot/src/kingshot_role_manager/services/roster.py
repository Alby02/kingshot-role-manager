import json
import logging
from datetime import datetime, timezone
from typing import TypedDict, TypeAlias, cast

from kingshot_role_manager.services.database import (
    bulk_update_roster,
    mark_absent,
    get_roster_for_alliance,
    get_linked_discord_ids_for_alliance,
)
from kingshot_role_manager.services.role_sync import sync_all_users, sync_selected_users

logger = logging.getLogger(__name__)

VALID_ALLIANCES = {"BOO", "ZEN"}
VALID_RANKS = {"R1", "R2", "R3", "R4", "R5"}


class RosterEntry(TypedDict):
    ign: str
    rank: str


class RosterSummary(TypedDict):
    processed: int
    removed: int
    sync_summary: dict[str, int]


class RosterDiff(TypedDict):
    current_count: int
    incoming_count: int
    added: list[str]
    removed: list[str]
    rank_changed: list[str]


RosterJson: TypeAlias = list[RosterEntry]

def validate_roster_json(data: object) -> None:
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

async def fetch_roster_attachment(attachment: discord.Attachment) -> RosterJson | None:
    try:
        raw = await attachment.read()
        decoded = json.loads(raw.decode("utf-8"))
        return cast(RosterJson, decoded)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to decode attachment: {e}")
        return None

async def process_roster(guild: discord.Guild, data: RosterJson, alliance: str) -> RosterSummary:
    timestamp = datetime.now(timezone.utc)
    bulk_update_roster(cast(list[dict[str, str]], data), alliance, timestamp)
    removed_count = mark_absent(alliance, timestamp)
    sync_summary = await sync_all_users(guild)
    return {
        "processed": len(data),
        "removed": removed_count,
        "sync_summary": sync_summary
    }


def compute_roster_diff(alliance: str, incoming: RosterJson) -> RosterDiff:
    """Compare incoming roster payload against the currently stored alliance roster."""
    current = get_roster_for_alliance(alliance)

    incoming_map: dict[str, str] = {}
    for entry in incoming:
        incoming_map[entry["ign"]] = entry.get("rank", "")

    current_igns = set(current.keys())
    incoming_igns = set(incoming_map.keys())

    added = sorted(incoming_igns - current_igns)
    removed = sorted(current_igns - incoming_igns)
    rank_changed = sorted(
        ign for ign in (incoming_igns & current_igns)
        if (incoming_map.get(ign) or "") != (current.get(ign) or "")
    )

    return {
        "current_count": len(current_igns),
        "incoming_count": len(incoming_igns),
        "added": added,
        "removed": removed,
        "rank_changed": rank_changed,
    }


async def force_reconcile_alliance(guild: discord.Guild, alliance: str, *, dry_run: bool = False) -> dict[str, int]:
    """Re-sync roles for linked users currently in a specific alliance."""
    discord_ids = get_linked_discord_ids_for_alliance(alliance)
    return await sync_selected_users(guild, discord_ids, dry_run=dry_run)
