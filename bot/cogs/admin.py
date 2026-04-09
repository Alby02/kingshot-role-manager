import discord
from discord.ext import commands
from discord import app_commands
import logging
from database import get_user_igns, register_user, set_diplomat, get_account_by_game_id
from role_sync import sync_roles_for_user
from services.kingshot_api import fetch_ign

logger = logging.getLogger(__name__)

class SetPlayerConfirmView(discord.ui.View):
    def __init__(self, admin_id: int, target_member: discord.Member, game_id: str, ign: str) -> None:
        super().__init__(timeout=60)
        self.admin_id = admin_id
        self.target_member = target_member
        self.game_id = game_id
        self.ign = ign

    @discord.ui.button(label="Yes, assign it", style=discord.ButtonStyle.green, custom_id="admin_confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            register_user(self.target_member.id, self.game_id, self.ign)
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
            await interaction.response.send_message(f"✅ Success! Linked account **{self.ign}** to {self.target_member.mention}.")
            if interaction.guild:
                await sync_roles_for_user(interaction.guild, self.target_member.id)
        except Exception as e:
            logger.error(f"Failed to setplayer: {e}")
            await interaction.response.send_message("❌ Database error occurred while forcing assignment.", ephemeral=True)

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="admin_confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.message.edit(content="❌ Setplayer cancelled.", view=self)

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

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
            game_id, ign, alliance, rank, is_diplomat = account
            alliance_str = alliance if alliance else "None"
            rank_str = rank if rank else "None"
            diplomat_str = " 🤝 Diplomat" if is_diplomat else ""
            embed.add_field(
                name=f"🎮 {ign} (ID: {game_id}){diplomat_str}",
                value=f"**Alliance:** {alliance_str} | **Rank:** {rank_str}",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setplayer", description="Manually link a game account to a user (Admin only).")
    @app_commands.describe(member="The user to link", game_id="The Kingshot Player ID")
    @app_commands.default_permissions(administrator=True)
    async def setplayer(self, interaction: discord.Interaction, member: discord.Member, game_id: str) -> None:
        await interaction.response.defer()

        ign = await fetch_ign(game_id)
        if not ign:
            await interaction.followup.send(f"❌ API Error: Could not find Kingshot account ID `{game_id}`.")
            return

        view = SetPlayerConfirmView(interaction.user.id, member, game_id, ign)
        await interaction.followup.send(f"Found account **{ign}**. Assign this account to {member.mention}?", view=view)

    def _has_officer_permission(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator:
            return True
        role_names = {r.name for r in member.roles}
        return "R4" in role_names or "R5" in role_names

    @app_commands.command(name="setdiplomat", description="Mark a game account as Diplomat (R4/R5/Admin only).")
    @app_commands.describe(game_id="The Kingshot Player ID")
    @app_commands.default_permissions(administrator=True)
    async def setdiplomat(self, interaction: discord.Interaction, game_id: str) -> None:
        if not self._has_officer_permission(interaction.user):
            await interaction.response.send_message("❌ Only **R4**, **R5**, or **Administrators** can use this command.", ephemeral=True)
            return

        account = get_account_by_game_id(game_id)
        if not account:
            await interaction.response.send_message(f"❌ No game account found with ID `{game_id}`.", ephemeral=True)
            return

        game_id, ign, discord_id, alliance, rank, is_diplomat = account

        if is_diplomat:
            await interaction.response.send_message(f"ℹ️ **{ign}** is already marked as Diplomat.", ephemeral=True)
            return

        set_diplomat(game_id, True)
        await interaction.response.send_message(f"✅ **{ign}** is now marked as **Diplomat**.")

        if discord_id and interaction.guild:
            await sync_roles_for_user(interaction.guild, discord_id)

    @app_commands.command(name="removediplomat", description="Remove Diplomat status from a game account (R4/R5/Admin only).")
    @app_commands.describe(game_id="The Kingshot Player ID")
    @app_commands.default_permissions(administrator=True)
    async def removediplomat(self, interaction: discord.Interaction, game_id: str) -> None:
        if not self._has_officer_permission(interaction.user):
            await interaction.response.send_message("❌ Only **R4**, **R5**, or **Administrators** can use this command.", ephemeral=True)
            return

        account = get_account_by_game_id(game_id)
        if not account:
            await interaction.response.send_message(f"❌ No game account found with ID `{game_id}`.", ephemeral=True)
            return

        game_id, ign, discord_id, alliance, rank, is_diplomat = account

        if not is_diplomat:
            await interaction.response.send_message(f"ℹ️ **{ign}** is not currently a Diplomat.", ephemeral=True)
            return

        set_diplomat(game_id, False)
        await interaction.response.send_message(f"✅ Removed **Diplomat** status from **{ign}**.")

        if discord_id and interaction.guild:
            await sync_roles_for_user(interaction.guild, discord_id)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
