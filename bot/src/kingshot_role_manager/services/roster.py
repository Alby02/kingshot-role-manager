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

    entries = cast(list[object], data)

    if len(entries) == 0:
        raise ValueError("JSON array is empty.")

    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {i} is not an object.")

        entry_obj = cast(dict[str, object], entry)
        ign_value = entry_obj.get("ign")
        if not isinstance(ign_value, str) or not ign_value.strip():
            raise ValueError(f"Entry {i} has invalid 'ign' (must be non-empty string).")

        if "rank" not in entry_obj:
            raise ValueError(f"Entry {i} is missing 'rank' field.")

        rank_value = entry_obj["rank"]
        if not isinstance(rank_value, str):
            raise ValueError(f"Entry {i} has invalid 'rank' (must be a string).")
        if rank_value not in VALID_RANKS:
            raise ValueError(f"Entry {i} has invalid rank '{rank_value}'. Must be one of {VALID_RANKS}.")


def _normalize_roster_json(data: object) -> RosterJson:
    validate_roster_json(data)
    normalized: RosterJson = []

    for raw_entry in cast(list[object], data):
        entry_obj = cast(dict[str, object], raw_entry)
        ign_value = cast(str, entry_obj["ign"]).strip()
        rank_value = cast(str, entry_obj["rank"])
        normalized.append({"ign": ign_value, "rank": rank_value})

    return normalized

def parse_roster_json(raw_bytes: bytes) -> RosterJson | None:
    try:
        decoded = json.loads(raw_bytes.decode("utf-8"))
        return _normalize_roster_json(decoded)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to decode roster data: {e}")
        return None

async def process_roster(guild: discord.Guild, data: RosterJson, alliance: str) -> RosterSummary:
    timestamp = datetime.now(timezone.utc)
    normalized_entries: list[dict[str, str]] = [
        {"ign": entry["ign"], "rank": entry["rank"]}
        for entry in data
    ]
    bulk_update_roster(normalized_entries, alliance, timestamp)
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
        incoming_map[entry["ign"]] = entry["rank"]

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
