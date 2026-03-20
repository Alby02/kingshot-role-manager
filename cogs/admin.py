import discord
from discord.ext import commands
import logging
from database import get_user_igns, register_user

logger = logging.getLogger(__name__)

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

        try:
            register_user(member.id, game_id, ign)
            await msg.edit(content=f"✅ Successfully linked account **{ign}** to {member.mention}.")
        except Exception as e:
            logger.error(f"Failed to setplayer: {e}")
            await msg.edit(content="❌ Database error occurred while forcing assignment.")

    @setplayer.error
    async def setplayer_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            await ctx.send("❌ You do not have the `Verifier` role required to use this command.")

async def setup(bot):
    await bot.add_cog(Admin(bot))
