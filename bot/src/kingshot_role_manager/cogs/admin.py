import discord
from discord.ext import commands
from discord import app_commands
from kingshot_role_manager.services.database import get_user_igns

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

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
