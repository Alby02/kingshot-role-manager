import discord
from discord.ext import commands
import logging
from database import get_user_igns, register_user
from cogs.verification import Verification

logger = logging.getLogger(__name__)

class SetPlayerConfirmView(discord.ui.View):
    def __init__(self, admin_id: int, target_member: discord.Member, game_id: str, ign: str):
        super().__init__(timeout=60)
        self.admin_id = admin_id
        self.target_member = target_member
        self.game_id = game_id
        self.ign = ign

    @discord.ui.button(label="Yes, assign it", style=discord.ButtonStyle.green, custom_id="admin_confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            register_user(self.target_member.id, self.game_id, self.ign)
            await interaction.response.send_message(f"✅ Success! Linked account **{self.ign}** to {self.target_member.mention}.")
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
        except Exception as e:
            logger.error(f"Failed to setplayer: {e}")
            await interaction.response.send_message("❌ Database error occurred while forcing assignment.", ephemeral=True)

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="admin_confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.message.edit(content="❌ Setplayer cancelled.", view=self)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="whois")
    async def whois(self, ctx, member: discord.Member = None):
        """Looks up the linked Kingshot game accounts for a Discord user."""
        if not member:
            await ctx.send("Please mention a user. Usage: `!whois @User`")
            return

        accounts = get_user_igns(member.id)
        if not accounts:
            await ctx.send(f"❌ {member.display_name} has no linked Kingshot game accounts.")
            return

        embed = discord.Embed(
            title=f"👤 Kingshot Accounts for {member.display_name}",
            color=discord.Color.purple()
        )
        
        for account in accounts:
            game_id, ign, alliance, rank = account
            alliance_str = alliance if alliance else "None"
            rank_str = rank if rank else "None"
            embed.add_field(
                name=f"🎮 {ign} (ID: {game_id})",
                value=f"**Alliance:** {alliance_str} | **Rank:** {rank_str}",
                inline=False
            )
            
        await ctx.send(embed=embed)

    @commands.command(name="setplayer")
    @commands.has_role("Verifier")
    async def setplayer(self, ctx, member: discord.Member = None, game_id: str = None):
        """Manually link a game account to a user (Verifier only)."""
        if not member or not game_id:
            await ctx.send("Usage: `!setplayer @User <GameID>`")
            return

        msg = await ctx.send(f"🔍 Searching API for ID `{game_id}`...")

        verification_cog = self.bot.get_cog("Verification")
        if not verification_cog:
            await msg.edit(content="❌ Verification system is currently offline.")
            return

        ign = await verification_cog.fetch_ign(game_id)
        
        if not ign:
            await msg.edit(content=f"❌ API Error: Could not find Kingshot account ID `{game_id}`.")
            return

        view = SetPlayerConfirmView(ctx.author.id, member, game_id, ign)
        await msg.edit(content=f"Found account **{ign}**. Assign this account to {member.mention}?", view=view)

    @setplayer.error
    async def setplayer_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            await ctx.send("❌ You do not have the `Verifier` role required to use this command.")

async def setup(bot):
    await bot.add_cog(Admin(bot))
