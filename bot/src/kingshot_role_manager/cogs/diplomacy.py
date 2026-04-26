import discord
from discord import app_commands
from discord.ext import commands

from kingshot_role_manager.services.database import get_account_by_game_id
from kingshot_role_manager.services.permissions import has_officer_permission
from kingshot_role_manager.ui.views import DiplomatActionView


class Diplomacy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setdiplomat", description="Mark a game account as Diplomat (R4/R5/Admin only).")
    @app_commands.describe(game_id="The Kingshot Player ID")
    @app_commands.default_permissions(administrator=True)
    async def setdiplomat(self, interaction: discord.Interaction, game_id: str) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_officer_permission(interaction.user):
            await interaction.response.send_message("Only R4, R5, or Administrators can use this command.", ephemeral=True)
            return

        account = get_account_by_game_id(game_id)
        if not account:
            await interaction.response.send_message(f"No game account found with ID `{game_id}`.", ephemeral=True)
            return

        ign = account["ign"]
        discord_id = account["discord_id"]
        alliance = account["alliance"]
        rank = account["rank"]
        is_diplomat = account["is_diplomat"]
        
        if is_diplomat:
            await interaction.response.send_message(f"**{ign}** is already marked as Diplomat.", ephemeral=True)
            return

        view = DiplomatActionView(interaction.user.id, game_id, ign, discord_id, is_adding=True)
        alliance_str = alliance if alliance else "None"
        rank_str = rank if rank else "None"
        embed = discord.Embed(
            title=f"Set Diplomat: {ign}",
            description=(
                f"**Alliance:** {alliance_str} | **Rank:** {rank_str}\n\n"
                "Are you sure you want to mark this player as a Diplomat?"
            ),
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="removediplomat", description="Remove Diplomat status from a game account (R4/R5/Admin only).")
    @app_commands.describe(game_id="The Kingshot Player ID")
    @app_commands.default_permissions(administrator=True)
    async def removediplomat(self, interaction: discord.Interaction, game_id: str) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_officer_permission(interaction.user):
            await interaction.response.send_message("Only R4, R5, or Administrators can use this command.", ephemeral=True)
            return

        account = get_account_by_game_id(game_id)
        if not account:
            await interaction.response.send_message(f"No game account found with ID `{game_id}`.", ephemeral=True)
            return

        ign = account["ign"]
        discord_id = account["discord_id"]
        alliance = account["alliance"]
        rank = account["rank"]
        is_diplomat = account["is_diplomat"]
        
        if not is_diplomat:
            await interaction.response.send_message(f"**{ign}** is not currently a Diplomat.", ephemeral=True)
            return

        view = DiplomatActionView(interaction.user.id, game_id, ign, discord_id, is_adding=False)
        alliance_str = alliance if alliance else "None"
        rank_str = rank if rank else "None"
        embed = discord.Embed(
            title=f"Remove Diplomat: {ign}",
            description=(
                f"**Alliance:** {alliance_str} | **Rank:** {rank_str}\n\n"
                "Are you sure you want to remove Diplomat status from this player?"
            ),
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Diplomacy(bot))
