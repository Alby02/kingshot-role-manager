import discord
from discord.ext import commands
from discord import app_commands
import logging
from services.roster import fetch_roster_attachment, validate_roster_json, process_roster

logger = logging.getLogger(__name__)

class Reconciliation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="upload_roster", description="Upload a roster JSON file for reconciliation (Admin/R4/R5).")
    @app_commands.describe(file="The .json roster file to upload")
    @app_commands.default_permissions(administrator=True)
    async def upload_roster(self, interaction: discord.Interaction, file: discord.Attachment) -> None:
        # We don't have an easy way to check R4/R5 dynamically via default_permissions alone, 
        # but we can enforce it in the command. Here we do an explicit check.
        has_permission = (
            interaction.user.guild_permissions.administrator
            or discord.utils.get(interaction.user.roles, name="R4")
            or discord.utils.get(interaction.user.roles, name="R5")
        )
        if not has_permission:
            await interaction.response.send_message("❌ Only **R4**, **R5**, or **Administrators** can upload roster files.", ephemeral=True)
            return

        if not file.filename.endswith('.json'):
            await interaction.response.send_message("❌ File must be a `.json` file.", ephemeral=True)
            return

        await interaction.response.defer()

        data = await fetch_roster_attachment(file)
        if data is None:
            await interaction.followup.send("❌ Failed to read or decode the JSON file. Invalid format.")
            return

        valid, result = validate_roster_json(data)
        if not valid:
            await interaction.followup.send(f"❌ Validation error: {result}")
            return

        alliance = result
        
        try:
            summary = await process_roster(interaction.guild, data, alliance)
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

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reconciliation(bot))
