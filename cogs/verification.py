import discord
from discord.ext import commands
import aiohttp
import logging
from database import register_user, update_ign

logger = logging.getLogger(__name__)

class ConfirmView(discord.ui.View):
    def __init__(self, discord_id: int, game_id: str, ign: str):
        super().__init__(timeout=60)
        self.discord_id = discord_id
        self.game_id = game_id
        self.ign = ign

    @discord.ui.button(label="Yes, this is me", style=discord.ButtonStyle.green, custom_id="confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            register_user(self.discord_id, self.game_id, self.ign)
            # Public success message
            await interaction.response.send_message(f"✅ Success! Your account **{self.ign}** has been linked.")
            
            # Disable buttons and close the prompt
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
            
        except Exception as e:
            logger.error(f"DB Error: {e}")
            await interaction.response.send_message("❌ Database error occurred while linking your account.", ephemeral=True)
            
    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.message.edit(content="❌ Verification cancelled.", view=self)

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_ign(self, player_id: str) -> str:
        url = f"https://kingshot.net/api/player-info?playerId={player_id}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "success" and "data" in data and "name" in data["data"]:
                            return data["data"]["name"]
            except Exception as e:
                logger.error(f"API Fetch Error: {e}")
        return None

    @commands.command(name="verify")
    async def verify(self, ctx, player_id: str = None):
        """Link a Kingshot account to your Discord."""
        if not player_id:
            await ctx.send("Please provide your Player ID. Usage: `!verify <PlayerID>`")
            return

        msg = await ctx.send("🔍 Searching Kingshot database...")

        ign = await self.fetch_ign(player_id)
        if not ign:
            await msg.edit(content=f"❌ Could not find an account with ID `{player_id}`. Please check and try again.")
            return

        view = ConfirmView(ctx.author.id, player_id, ign)
        await msg.edit(content=f"Found account **{ign}**. Is this your username?", view=view)

    @commands.command(name="sync")
    async def sync(self, ctx, player_id: str = None):
        """Force an API re-sync of a cached IGN."""
        if not player_id:
            await ctx.send("Please provide the Player ID to sync. Usage: `!sync <PlayerID>`")
            return

        msg = await ctx.send("🔍 Fetching latest info...")

        ign = await self.fetch_ign(player_id)
        if not ign:
            await msg.edit(content=f"❌ Could not find an account with ID `{player_id}`.")
            return

        success = update_ign(ctx.author.id, player_id, ign)
        if success:
            await msg.edit(content=f"✅ Successfully refreshed! Your IGN is now listed as **{ign}**.")
        else:
            await msg.edit(content=f"❌ Error: The account ID `{player_id}` is not linked to your Discord profile.")


async def setup(bot):
    await bot.add_cog(Verification(bot))
