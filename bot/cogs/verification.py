import discord
from discord.ext import commands
from discord import app_commands
import logging
from services.database import register_user, update_player_data
from services.role_sync import sync_roles_for_user
from services.kingshot_api import fetch_ign

logger = logging.getLogger(__name__)

class ConfirmView(discord.ui.View):
    def __init__(self, discord_id: int, game_id: str, ign: str, kingdom: int, level: int) -> None:
        super().__init__(timeout=60)
        self.discord_id = discord_id
        self.game_id = game_id
        self.ign = ign
        self.kingdom = kingdom
        self.level = level

    @discord.ui.button(label="Yes, this is me", style=discord.ButtonStyle.green, custom_id="confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            register_user(self.discord_id, self.game_id, self.ign, self.kingdom, self.level)

            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)

            await interaction.followup.send(f"✅ Success! Your account **{self.ign}** has been linked.", ephemeral=True)

            if interaction.guild:
                await sync_roles_for_user(interaction.guild, self.discord_id)
            
        except Exception as e:
            logger.error(f"DB Error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Database error occurred while linking your account.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Database error occurred while linking your account.", ephemeral=True)
            
    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Verification cancelled.", view=self)

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

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Verification(bot))
