"""
role_sync.py – Data-driven Discord role assignment.

Roles are computed from the database state and applied to Discord members.
This module is called by verification, reconciliation, and admin cogs.
"""

import discord
import logging
from database import get_discord_user_roles, get_all_linked_discord_ids

logger = logging.getLogger(__name__)

# Discord role names the bot manages. These must exist on the server.
MANAGED_ROLES = {
    "alliances": {"BOO", "ZEN"},
    "ranks": {"R1", "R2", "R3", "R4", "R5"},
    "status": {"Guest", "Member", "Diplomat", "Ex-Member"},
}

ALL_MANAGED = MANAGED_ROLES["alliances"] | MANAGED_ROLES["ranks"] | MANAGED_ROLES["status"]


def _get_role(guild: discord.Guild, name: str) -> discord.Role | None:
    """Look up a role by name. Returns None if not found."""
    role = discord.utils.get(guild.roles, name=name)
    if not role:
        logger.warning(f"Role '{name}' not found on server '{guild.name}'. Skipping.")
    return role


async def sync_roles_for_user(guild: discord.Guild, discord_id: int) -> None:
    """
    Compute the correct set of Discord roles for a single user based on
    their database state, then add/remove roles to match.
    """
    member = guild.get_member(discord_id)
    if not member:
        logger.debug(f"Discord user {discord_id} is not on the server. Skipping role sync.")
        return

    data = get_discord_user_roles(discord_id)

    # --- Compute desired roles ---
    desired: set[str] = set()

    if not data["has_accounts"]:
        # No linked accounts at all – nothing to assign
        return

    if data["alliances"]:
        # Active alliance member(s)
        desired.add("Member")
        desired |= data["alliances"]  # e.g. {"BOO"}, {"ZEN"}, or both
        desired |= data["ranks"]      # e.g. {"R4", "R5"}
    elif data["had_alliance"]:
        # Was in an alliance before but no longer
        desired.add("Ex-Member")
    else:
        # Linked account but never appeared in a roster
        desired.add("Guest")

    if data["is_diplomat"]:
        desired.add("Diplomat")

    # --- Diff against current roles ---
    current_managed = {r.name for r in member.roles if r.name in ALL_MANAGED}

    roles_to_add = desired - current_managed
    roles_to_remove = current_managed - desired

    # Apply additions
    for role_name in roles_to_add:
        role = _get_role(guild, role_name)
        if role:
            try:
                await member.add_roles(role, reason="Auto role-sync from DB")
                logger.info(f"[+] {role_name} → {member.display_name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to add role {role_name} to {member.display_name}")
            except discord.HTTPException as e:
                logger.error(f"Failed to add role {role_name}: {e}")

    # Apply removals
    for role_name in roles_to_remove:
        role = _get_role(guild, role_name)
        if role:
            try:
                await member.remove_roles(role, reason="Auto role-sync from DB")
                logger.info(f"[-] {role_name} ✕ {member.display_name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to remove role {role_name} from {member.display_name}")
            except discord.HTTPException as e:
                logger.error(f"Failed to remove role {role_name}: {e}")


async def sync_all_users(guild: discord.Guild) -> dict[str, int]:
    """
    Bulk-sync roles for every linked Discord user.
    Returns a summary dict: {"synced": int, "skipped": int, "errors": int}
    """
    discord_ids = get_all_linked_discord_ids()
    summary = {"synced": 0, "skipped": 0, "errors": 0}

    for discord_id in discord_ids:
        try:
            member = guild.get_member(discord_id)
            if not member:
                summary["skipped"] += 1
                continue
            await sync_roles_for_user(guild, discord_id)
            summary["synced"] += 1
        except Exception as e:
            logger.error(f"Error syncing roles for {discord_id}: {e}")
            summary["errors"] += 1

    logger.info(f"Bulk role sync complete: {summary}")
    return summary
