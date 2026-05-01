import discord
from discord.ext import commands
from discord import app_commands
import logging

from kingshot_role_manager.services.database import get_user_igns, update_player_data
from kingshot_role_manager.services.role_sync import sync_roles_for_user
from kingshot_role_manager.services.kingshot_api import fetch_ign
from kingshot_role_manager.services.permissions import (
    has_player_manager_permission,
    bootstrap_management_roles,
)
from kingshot_role_manager.ui.views import LinkAccountView

logger = logging.getLogger(__name__)

class Identity(commands.Cog):
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

        view = LinkAccountView(
            actor_id=interaction.user.id, 
            target_member_id=interaction.user.id,
            game_id=player_id, 
            ign=ign, 
            kingdom=kingdom, 
            level=level
        )
        
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

    @app_commands.command(name="whois", description="Looks up the linked Kingshot game accounts for a Discord user.")
    @app_commands.describe(member="The Discord member to look up")
    async def whois(self, interaction: discord.Interaction, member: discord.Member) -> None:
        accounts = get_user_igns(member.id)
        if not accounts:
            await interaction.response.send_message(f"❌ {member.display_name} has no linked Kingshot game accounts.")
            return

        embed = discord.Embed(
            title=f"👤 Kingshot Accounts for {member.display_name}",
            color=discord.Color.purple()
        )
        
        for account in accounts:
            alliance_str = account["alliance"] if account["alliance"] else "None"
            rank_str = account["rank"] if account["rank"] else "None"
            diplomat_str = " 🤝 Diplomat" if account["is_diplomat"] else ""
            embed.add_field(
                name=f"🎮 {account['ign']} (ID: {account['game_id']}){diplomat_str}",
                value=f"**Kingdom:** {account['kingdom']} | **Level:** {account['level']}\n**Alliance:** {alliance_str} | **Rank:** {rank_str}",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setplayer", description="Manually link a game account to a user (roster-manager/Admin).")
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

        view = LinkAccountView(
            actor_id=interaction.user.id,
            target_member_id=member.id,
            game_id=game_id,
            ign=ign,
            kingdom=kingdom,
            level=level
        )
        embed = discord.Embed(
            title=f"Assign Account: {ign}",
            description=f"**Kingdom:** {kingdom} | **Level:** {level}\n\nAssign this Kingshot account to {member.mention}?",
            color=discord.Color.blue(),
        )
        if photo:
            embed.set_thumbnail(url=photo)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="removeplayer", description="Remove a linked game account from a user (roster-manager/Admin).")
    @app_commands.describe(member="The user to unlink", game_id="The Kingshot Player ID to remove (if they have multiple)")
    @app_commands.default_permissions(administrator=True)
    async def removeplayer(self, interaction: discord.Interaction, member: discord.Member, game_id: str | None = None) -> None:
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

        from kingshot_role_manager.services.database import get_user_igns, delete_player_account
        from kingshot_role_manager.ui.views import RemoveAccountSelect, RemoveAccountView

        if game_id:
            await interaction.response.defer(ephemeral=True)
            try:
                delete_player_account(game_id)
                await interaction.followup.send(f"✅ Successfully unlinked account ID `{game_id}` from {member.mention}.", ephemeral=True)
                if interaction.guild:
                    await sync_roles_for_user(interaction.guild, member.id)
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to unlink account: {e}", ephemeral=True)
            return

        accounts = get_user_igns(member.id)
        if not accounts:
            await interaction.response.send_message(f"❌ {member.display_name} has no linked Kingshot game accounts.", ephemeral=True)
            return

        if len(accounts) == 1:
            g_id = accounts[0]["game_id"]
            await interaction.response.defer(ephemeral=True)
            try:
                delete_player_account(g_id)
                await interaction.followup.send(f"✅ Successfully unlinked account **{accounts[0]['ign']}** (ID: `{g_id}`) from {member.mention}.", ephemeral=True)
                if interaction.guild:
                    await sync_roles_for_user(interaction.guild, member.id)
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to unlink account: {e}", ephemeral=True)
            return

        view = RemoveAccountView(target_member=member)
        view.add_item(RemoveAccountSelect(accounts)) # type: ignore
        await interaction.response.send_message(
            f"{member.display_name} has multiple linked accounts. Please select which one to remove:",
            view=view,
            ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Identity(bot))
