import discord
from discord.ext import commands
from discord import app_commands
import logging
from kingshot_role_manager.services.roster import (
    fetch_roster_attachment,
    validate_roster_json,
    process_roster,
    compute_roster_diff,
    force_reconcile_alliance,
    RosterDiff,
)
from kingshot_role_manager.services.permissions import (
    bootstrap_management_roles,
    has_roster_manager_permission,
)

logger = logging.getLogger(__name__)

class Reconciliation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="upload_roster", description="Upload a roster JSON file for reconciliation (roster-manager/Admin).")
    @app_commands.describe(
        file="The .json roster file to upload",
        alliance="Alliance this roster belongs to",
    )
    @app_commands.choices(alliance=[
        app_commands.Choice(name="BOO", value="BOO"),
        app_commands.Choice(name="ZEN", value="ZEN"),
    ])
    @app_commands.default_permissions(administrator=True)
    async def upload_roster(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        alliance: str,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        guild = interaction.guild
        if guild:
            await bootstrap_management_roles(guild, interaction.user)
        else:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        if not has_roster_manager_permission(interaction.user):
            await interaction.response.send_message(
                "Only roster-manager or Administrators can upload roster files.",
                ephemeral=True,
            )
            return

        if not file.filename.endswith('.json'):
            await interaction.response.send_message("❌ File must be a `.json` file.", ephemeral=True)
            return

        await interaction.response.defer()

        data = await fetch_roster_attachment(file)
        if data is None:
            await interaction.followup.send("❌ Failed to read or decode the JSON file. Invalid format.")
            return

        try:
            validate_roster_json(data)
        except ValueError as e:
            await interaction.followup.send(f"❌ Validation error: {e}")
            return
        
        try:
            summary = await process_roster(guild, data, alliance)
        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            await interaction.followup.send(f"❌ Reconciliation error: `{e}`")
            return

        embed = discord.Embed(
            title=f"✅ Roster Reconciliation Complete — {alliance}",
            color=discord.Color.green()
        )
        embed.add_field(name="📋 Roster Entries", value=str(summary["processed"]), inline=True)
        embed.add_field(name="🚪 Removed (absent)", value=str(summary["removed"]), inline=True)
        
        sync_stats = summary["sync_summary"]
        embed.add_field(
            name="🔄 Role Sync",
            value=f"Synced: {sync_stats['synced']} | Skipped: {sync_stats['skipped']} | Errors: {sync_stats['errors']}",
            inline=False,
        )
        embed.set_footer(text=f"Uploaded by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="roster_diff", description="Preview roster changes without applying them.")
    @app_commands.describe(
        file="The .json roster file to compare",
        alliance="Alliance this roster belongs to",
    )
    @app_commands.choices(alliance=[
        app_commands.Choice(name="BOO", value="BOO"),
        app_commands.Choice(name="ZEN", value="ZEN"),
    ])
    @app_commands.default_permissions(administrator=True)
    async def roster_diff(self, interaction: discord.Interaction, file: discord.Attachment, alliance: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        guild = interaction.guild
        if guild:
            await bootstrap_management_roles(guild, interaction.user)

        if not has_roster_manager_permission(interaction.user):
            await interaction.response.send_message("Only roster-manager or Administrators can use this command.", ephemeral=True)
            return

        if not file.filename.endswith('.json'):
            await interaction.response.send_message("File must be a `.json` file.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        data = await fetch_roster_attachment(file)
        if data is None:
            await interaction.followup.send("Failed to read or decode the JSON file. Invalid format.", ephemeral=True)
            return

        try:
            validate_roster_json(data)
            diff: RosterDiff = compute_roster_diff(alliance, data)
        except ValueError as e:
            await interaction.followup.send(f"Validation error: {e}", ephemeral=True)
            return
        except Exception as e:
            logger.error(f"Roster diff failed: {e}")
            await interaction.followup.send(f"Roster diff failed: `{e}`", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Roster Diff Preview - {alliance}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Current", value=str(diff["current_count"]), inline=True)
        embed.add_field(name="Incoming", value=str(diff["incoming_count"]), inline=True)
        embed.add_field(name="Added", value=str(len(diff["added"])), inline=True)
        embed.add_field(name="Removed", value=str(len(diff["removed"])), inline=True)
        embed.add_field(name="Rank Changed", value=str(len(diff["rank_changed"])), inline=True)

        sample_added = ", ".join(diff["added"][:10]) or "None"
        sample_removed = ", ".join(diff["removed"][:10]) or "None"
        sample_rank = ", ".join(diff["rank_changed"][:10]) or "None"
        embed.add_field(name="Sample Added", value=sample_added, inline=False)
        embed.add_field(name="Sample Removed", value=sample_removed, inline=False)
        embed.add_field(name="Sample Rank Changes", value=sample_rank, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="reconcile_alliance", description="Force role reconciliation for one alliance.")
    @app_commands.describe(alliance="Alliance to reconcile", dry_run="If true, preview only with no role changes")
    @app_commands.choices(alliance=[
        app_commands.Choice(name="BOO", value="BOO"),
        app_commands.Choice(name="ZEN", value="ZEN"),
    ])
    @app_commands.default_permissions(administrator=True)
    async def reconcile_alliance(self, interaction: discord.Interaction, alliance: str, dry_run: bool = True) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        guild = interaction.guild
        if guild:
            await bootstrap_management_roles(guild, interaction.user)

        if not has_roster_manager_permission(interaction.user):
            await interaction.response.send_message("Only roster-manager or Administrators can use this command.", ephemeral=True)
            return

        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            summary = await force_reconcile_alliance(interaction.guild, alliance, dry_run=dry_run)
        except Exception as e:
            logger.error(f"Force reconciliation failed: {e}")
            await interaction.followup.send(f"Force reconciliation failed: `{e}`", ephemeral=True)
            return

        title = f"Alliance Reconciliation Preview - {alliance}" if dry_run else f"Alliance Reconciliation Complete - {alliance}"
        color = discord.Color.orange() if dry_run else discord.Color.green()
        embed = discord.Embed(title=title, color=color)

        if dry_run:
            embed.add_field(name="Members with Changes", value=str(summary.get("would_change", 0)), inline=True)
            embed.add_field(name="Roles to Add", value=str(summary.get("would_add", 0)), inline=True)
            embed.add_field(name="Roles to Remove", value=str(summary.get("would_remove", 0)), inline=True)
            embed.add_field(name="Skipped", value=str(summary.get("skipped", 0)), inline=True)
            embed.add_field(name="Errors", value=str(summary.get("errors", 0)), inline=True)
        else:
            embed.add_field(name="Synced", value=str(summary.get("synced", 0)), inline=True)
            embed.add_field(name="Skipped", value=str(summary.get("skipped", 0)), inline=True)
            embed.add_field(name="Errors", value=str(summary.get("errors", 0)), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reconciliation(bot))
