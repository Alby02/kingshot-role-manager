"""
role_sync.py – Data-driven Discord role assignment.

Roles are computed from the database state and applied to Discord members.
This module is called by verification, reconciliation, and admin cogs.
"""

import discord
import logging
from typing import TypedDict

from kingshot_role_manager.services.database import (
    get_discord_user_roles,
    get_all_linked_discord_ids,
    UserRoleData,
)
from kingshot_role_manager.services.permissions import ensure_role_exists

logger = logging.getLogger(__name__)

# Discord role names the bot manages.
MANAGED_ROLES = {
    "alliances": {"BOO", "ZEN"},
    "ranks": {"R1", "R2", "R3", "R4", "R5"},
    "status": {"Guest", "Member", "Diplomat", "Ex-Member"},
}

ALL_MANAGED = MANAGED_ROLES["alliances"] | MANAGED_ROLES["ranks"] | MANAGED_ROLES["status"]


class RolePreview(TypedDict):
    member: discord.Member
    to_add: set[str]
    to_remove: set[str]


def _desired_roles_from_data(data: UserRoleData) -> set[str]:
    desired: set[str] = set()

    if not data["has_accounts"]:
        return desired

    if data["alliances"]:
        desired.add("Member")
        desired |= data["alliances"]
        desired |= data["ranks"]
    elif data["had_alliance"]:
        desired.add("Ex-Member")
    else:
        desired.add("Guest")

    if data["is_diplomat"]:
        desired.add("Diplomat")

    return desired


async def _get_or_create_role(guild: discord.Guild, name: str) -> discord.Role | None:
    """Look up a role by name, creating it if needed."""
    role = discord.utils.get(guild.roles, name=name)
    if role:
        return role

    role = await ensure_role_exists(
        guild,
        name,
        reason="Auto-created required role for Kingshot role sync",
    )
    if not role:
        logger.warning("Role '%s' missing and could not be created on server '%s'.", name, guild.name)
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

    desired = _desired_roles_from_data(data)
    if not desired and not data["has_accounts"]:
        return

    # --- Diff against current roles ---
    current_managed = {r.name for r in member.roles if r.name in ALL_MANAGED}

    roles_to_add = desired - current_managed
    roles_to_remove = current_managed - desired

    # Apply additions
    for role_name in roles_to_add:
        role = await _get_or_create_role(guild, role_name)
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
        role = await _get_or_create_role(guild, role_name)
        if role:
            try:
                await member.remove_roles(role, reason="Auto role-sync from DB")
                logger.info(f"[-] {role_name} ✕ {member.display_name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to remove role {role_name} from {member.display_name}")
            except discord.HTTPException as e:
                logger.error(f"Failed to remove role {role_name}: {e}")


async def preview_roles_for_user(guild: discord.Guild, discord_id: int) -> RolePreview | None:
    member = guild.get_member(discord_id)
    if not member:
        return None

    data = get_discord_user_roles(discord_id)
    if not data["has_accounts"]:
        return None

    desired = _desired_roles_from_data(data)
    current_managed = {r.name for r in member.roles if r.name in ALL_MANAGED}

    return {
        "member": member,
        "to_add": desired - current_managed,
        "to_remove": current_managed - desired,
    }


async def sync_selected_users(
    guild: discord.Guild,
    discord_ids: list[int],
    *,
    dry_run: bool = False,
) -> dict[str, int]:
    summary = {
        "synced": 0,
        "skipped": 0,
        "errors": 0,
        "would_change": 0,
        "would_add": 0,
        "would_remove": 0,
    }

    for discord_id in discord_ids:
        try:
            member = guild.get_member(discord_id)
            if not member:
                summary["skipped"] += 1
                continue

            if dry_run:
                preview = await preview_roles_for_user(guild, discord_id)
                if preview is None:
                    summary["skipped"] += 1
                    continue

                to_add = preview["to_add"]
                to_remove = preview["to_remove"]
                if to_add or to_remove:
                    summary["would_change"] += 1
                    summary["would_add"] += len(to_add)
                    summary["would_remove"] += len(to_remove)
            else:
                await sync_roles_for_user(guild, discord_id)
                summary["synced"] += 1
        except Exception as e:
            logger.error(f"Error syncing roles for {discord_id}: {e}")
            summary["errors"] += 1

    return summary


async def sync_all_users(guild: discord.Guild) -> dict[str, int]:
    """
    Bulk-sync roles for every linked Discord user.
    Returns a summary dict: {"synced": int, "skipped": int, "errors": int}
    """
    discord_ids = get_all_linked_discord_ids()
    summary = await sync_selected_users(guild, discord_ids)

    logger.info(f"Bulk role sync complete: {summary}")
    return summary
