"""
reconciliation.py – Watches #roster-updates for JSON uploads and
runs the state reconciliation engine.
"""

import discord
from discord.ext import commands
import json
import logging
import os
from datetime import datetime, timezone

from database import bulk_update_roster, mark_absent
from role_sync import sync_all_users

logger = logging.getLogger(__name__)

ROSTER_CHANNEL_ID = os.environ.get("ROSTER_CHANNEL_ID", "")
VALID_ALLIANCES = {"BOO", "ZEN"}
VALID_RANKS = {"R1", "R2", "R3", "R4", "R5"}


def validate_roster_json(data) -> tuple[bool, str]:
    """Validate the structure of a roster JSON payload."""
    if not isinstance(data, list):
        return False, "JSON must be an array of objects."

    if len(data) == 0:
        return False, "JSON array is empty."

    alliances_found = set()

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            return False, f"Entry {i} is not an object."
        if "ign" not in entry:
            return False, f"Entry {i} is missing 'ign' field."
        if not isinstance(entry["ign"], str) or not entry["ign"].strip():
            return False, f"Entry {i} has invalid 'ign' (must be non-empty string)."

        rank = entry.get("rank")
        if rank and rank not in VALID_RANKS:
            return False, f"Entry {i} has invalid rank '{rank}'. Must be one of {VALID_RANKS}."

        alliance = entry.get("alliance")
        if alliance:
            if alliance not in VALID_ALLIANCES:
                return False, f"Entry {i} has invalid alliance '{alliance}'. Must be one of {VALID_ALLIANCES}."
            alliances_found.add(alliance)

    if len(alliances_found) > 1:
        return False, f"JSON contains mixed alliances {alliances_found}. Upload one alliance roster at a time."

    if len(alliances_found) == 0:
        return False, "No alliance tag found in any entry. Each entry needs an 'alliance' field."

    return True, alliances_found.pop()


class Reconciliation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return

        # Only listen in the roster channel
        if not ROSTER_CHANNEL_ID or str(message.channel.id) != ROSTER_CHANNEL_ID:
            return

        # Check for .json attachments
        json_attachments = [a for a in message.attachments if a.filename.endswith(".json")]
        if not json_attachments:
            return

        # Permission check: R4, R5, or Administrator
        has_permission = (
            message.author.guild_permissions.administrator
            or discord.utils.get(message.author.roles, name="R4")
            or discord.utils.get(message.author.roles, name="R5")
        )
        if not has_permission:
            await message.reply(
                "❌ Only **R4**, **R5**, or **Administrators** can upload roster files.",
                delete_after=15,
            )
            return

        # Process the first .json attachment
        attachment = json_attachments[0]
        status_msg = await message.reply("📥 Downloading roster file...")

        try:
            raw = await attachment.read()
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            await status_msg.edit(content=f"❌ Invalid JSON file: `{e}`")
            return

        # Validate structure
        valid, result = validate_roster_json(data)
        if not valid:
            await status_msg.edit(content=f"❌ Validation error: {result}")
            return

        alliance = result  # The alliance tag extracted from the JSON
        await status_msg.edit(content=f"⚙️ Processing **{alliance}** roster ({len(data)} entries)...")

        # ---- Run reconciliation ----
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            # Step 1: Upsert all roster entries
            bulk_update_roster(data, alliance, timestamp)

            # Step 2: Mark absent accounts (those NOT updated in this scan)
            removed_count = mark_absent(alliance, timestamp)

            # Step 3: Sync Discord roles for all linked users
            guild = message.guild
            sync_summary = await sync_all_users(guild)

        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            await status_msg.edit(content=f"❌ Reconciliation error: `{e}`")
            return

        # ---- Build summary embed ----
        embed = discord.Embed(
            title=f"✅ Roster Reconciliation Complete — {alliance}",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="📋 Roster Entries", value=str(len(data)), inline=True)
        embed.add_field(name="🚪 Removed (absent)", value=str(removed_count), inline=True)
        embed.add_field(
            name="🔄 Role Sync",
            value=f"Synced: {sync_summary['synced']} | Skipped: {sync_summary['skipped']} | Errors: {sync_summary['errors']}",
            inline=False,
        )
        embed.set_footer(text=f"Uploaded by {message.author.display_name}")

        await status_msg.edit(content=None, embed=embed)
        logger.info(f"Reconciliation complete for {alliance}: {len(data)} entries, {removed_count} removed")


async def setup(bot):
    await bot.add_cog(Reconciliation(bot))
