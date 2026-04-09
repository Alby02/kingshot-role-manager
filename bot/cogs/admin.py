import discord
from discord.ext import commands
from discord import app_commands
import logging
from services.database import get_user_igns, register_user, set_diplomat, get_account_by_game_id
from services.role_sync import sync_roles_for_user
from services.kingshot_api import fetch_ign

logger = logging.getLogger(__name__)

class SetPlayerConfirmView(discord.ui.View):
    def __init__(self, admin_id: int, target_member: discord.Member, game_id: str, ign: str, kingdom: int, level: int) -> None:
        super().__init__(timeout=60)
        self.admin_id = admin_id
        self.target_member = target_member
        self.game_id = game_id
        self.ign = ign
        self.kingdom = kingdom
        self.level = level

    @discord.ui.button(label="Yes, assign it", style=discord.ButtonStyle.green, custom_id="admin_confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            register_user(self.target_member.id, self.game_id, self.ign, self.kingdom, self.level)
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"✅ Success! Linked account **{self.ign}** to {self.target_member.mention}.", ephemeral=True)
            if interaction.guild:
                await sync_roles_for_user(interaction.guild, self.target_member.id)
        except Exception as e:
            logger.error(f"Failed to setplayer: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Database error occurred while forcing assignment.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Database error occurred while forcing assignment.", ephemeral=True)

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="admin_confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Setplayer cancelled.", view=self)

class DiplomatConfirmView(discord.ui.View):
    def __init__(self, admin_id: int, game_id: str, ign: str, discord_id: int, is_adding: bool) -> None:
        super().__init__(timeout=60)
        self.admin_id = admin_id
        self.game_id = game_id
        self.ign = ign
        self.discord_id = discord_id
        self.is_adding = is_adding

    @discord.ui.button(label="Yes, confirm", style=discord.ButtonStyle.green, custom_id="dip_confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            set_diplomat(self.game_id, self.is_adding)
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            
            action_str = "marked as **Diplomat**" if self.is_adding else "no longer a **Diplomat**"
            await interaction.followup.send(f"✅ **{self.ign}** is {action_str}.", ephemeral=True)
            
            if self.discord_id and interaction.guild:
                await sync_roles_for_user(interaction.guild, self.discord_id)
        except Exception as e:
            logger.error(f"Failed to change diplomat status: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Database error occurred.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Database error occurred.", ephemeral=True)

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="dip_confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Action cancelled.", view=self)

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
            game_id, ign, alliance, rank, is_diplomat, kingdom, level = account
            alliance_str = alliance if alliance else "None"
            rank_str = rank if rank else "None"
            diplomat_str = " 🤝 Diplomat" if is_diplomat else ""
            embed.add_field(
                name=f"🎮 {ign} (ID: {game_id}){diplomat_str}",
                value=f"**Kingdom:** {kingdom} | **Level:** {level}\n**Alliance:** {alliance_str} | **Rank:** {rank_str}",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setplayer", description="Manually link a game account to a user (Admin only).")
    @app_commands.describe(member="The user to link", game_id="The Kingshot Player ID")
    @app_commands.default_permissions(administrator=True)
    async def setplayer(self, interaction: discord.Interaction, member: discord.Member, game_id: str) -> None:
        await interaction.response.defer(ephemeral=True)

        player_data = await fetch_ign(game_id)
        if not player_data:
            await interaction.followup.send(f"❌ API Error: Could not find Kingshot account ID `{game_id}`.", ephemeral=True)
            return

        ign = player_data["name"]
        kingdom = player_data.get("kingdom", 0)
        level = player_data.get("level", 0)
        photo = player_data.get("profilePhoto")

        view = SetPlayerConfirmView(interaction.user.id, member, game_id, ign, kingdom, level)
        embed = discord.Embed(
            title=f"Assign Account: {ign}", 
            description=f"**Kingdom:** {kingdom} | **Level:** {level}\n\nAssign this Kingshot account to {member.mention}?", 
            color=discord.Color.blue()
        )
        if photo:
            embed.set_thumbnail(url=photo)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

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

        view = DiplomatConfirmView(interaction.user.id, game_id, ign, discord_id, is_adding=True)
        alliance_str = alliance if alliance else "None"
        rank_str = rank if rank else "None"
        embed = discord.Embed(
            title=f"Set Diplomat: {ign}",
            description=f"**Alliance:** {alliance_str} | **Rank:** {rank_str}\n\nAre you sure you want to mark this player as a Diplomat?",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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

        view = DiplomatConfirmView(interaction.user.id, game_id, ign, discord_id, is_adding=False)
        alliance_str = alliance if alliance else "None"
        rank_str = rank if rank else "None"
        embed = discord.Embed(
            title=f"Remove Diplomat: {ign}",
            description=f"**Alliance:** {alliance_str} | **Rank:** {rank_str}\n\nAre you sure you want to completely remove Diplomat status from this player?",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
