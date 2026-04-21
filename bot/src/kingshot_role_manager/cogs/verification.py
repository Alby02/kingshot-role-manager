import discord
from discord.ext import commands
from discord import app_commands
import logging
from kingshot_role_manager.services.database import update_player_data
from kingshot_role_manager.services.role_sync import sync_roles_for_user
from kingshot_role_manager.services.kingshot_api import fetch_ign
from kingshot_role_manager.services.permissions import (
    has_player_manager_permission,
    bootstrap_management_roles,
)
from kingshot_role_manager.ui.verification_views import ConfirmView, SetPlayerConfirmView

logger = logging.getLogger(__name__)

class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="verify", description="Link a Kingshot account to your Discord.")
    @app_commands.describe(player_id="Your Kingshot Player ID")
    async def verify(self, interaction: discord.Interaction, player_id: str) -> None:
        await interaction.response.defer(ephemeral=True)
        
        player_data = await fetch_ign(player_id)
        if not player_data:
            await interaction.followup.send(f"❌ Could not find an account with ID `{player_id}`. Please check and try again.", ephemeral=True)
            return

        ign = player_data["name"]
        kingdom = player_data.get("kingdom", 0)
        level = player_data.get("level", 0)
        photo = player_data.get("profilePhoto")

        view = ConfirmView(interaction.user.id, player_id, ign, kingdom, level)
        embed = discord.Embed(
            title=f"Verify Account: {ign}", 
            description=f"**Kingdom:** {kingdom} | **Level:** {level}\n\nIs this your Kingshot account?", 
            color=discord.Color.blue()
        )
        if photo:
            embed.set_thumbnail(url=photo)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="sync", description="Force an API re-sync of a cached IGN.")
    @app_commands.describe(player_id="The Kingshot Player ID to sync")
    async def sync(self, interaction: discord.Interaction, player_id: str) -> None:
        await interaction.response.defer(ephemeral=True)

        player_data = await fetch_ign(player_id)
        if not player_data:
            await interaction.followup.send(f"❌ Could not find an account with ID `{player_id}`.", ephemeral=True)
            return

        ign = player_data["name"]
        kingdom = player_data.get("kingdom", 0)
        level = player_data.get("level", 0)

        success = update_player_data(interaction.user.id, player_id, ign, kingdom, level)
        if success:
            await interaction.followup.send(f"✅ Successfully refreshed! Your IGN is now listed as **{ign}** (Level {level}, K{kingdom}).", ephemeral=True)
            if interaction.guild:
                await sync_roles_for_user(interaction.guild, interaction.user.id)
        else:
            await interaction.followup.send(f"❌ Error: The account ID `{player_id}` is not linked to your Discord profile.", ephemeral=True)

    @app_commands.command(name="setplayer", description="Manually link a game account to a user.")
    @app_commands.describe(member="The user to link", game_id="The Kingshot Player ID")
    @app_commands.default_permissions(administrator=True)
    async def setplayer(self, interaction: discord.Interaction, member: discord.Member, game_id: str) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        guild = interaction.guild
        if guild:
            await bootstrap_management_roles(guild, interaction.user)

        if not has_player_manager_permission(interaction.user):
            await interaction.response.send_message(
                "You need one of these roles: roster-manager, player-manager, or Administrator.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        player_data = await fetch_ign(game_id)
        if not player_data:
            await interaction.followup.send(f"API error: could not find Kingshot account ID `{game_id}`.", ephemeral=True)
            return

        ign = player_data["name"]
        kingdom = player_data.get("kingdom", 0)
        level = player_data.get("level", 0)
        photo = player_data.get("profilePhoto")

        view = SetPlayerConfirmView(interaction.user.id, member, game_id, ign, kingdom, level)
        embed = discord.Embed(
            title=f"Assign Account: {ign}",
            description=f"**Kingdom:** {kingdom} | **Level:** {level}\n\nAssign this Kingshot account to {member.mention}?",
            color=discord.Color.blue(),
        )
        if photo:
            embed.set_thumbnail(url=photo)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Verification(bot))
