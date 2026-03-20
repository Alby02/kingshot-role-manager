import discord
from discord.ext import commands
import logging
import os

logger = logging.getLogger(__name__)

# Load PING_CHANNEL_IDS from environment, expecting a comma-separated list of IDs
ping_channels_str = os.environ.get("PING_CHANNEL_IDS", "")
PING_CHANNEL_IDS = [int(cid.strip()) for cid in ping_channels_str.split(',') if cid.strip().isdigit()]

EVENT_ROLES = {
    "🐻": "Bearhunt",
    "⚔️": "Arena"
}

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.channel_id not in PING_CHANNEL_IDS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        emoji_name = payload.emoji.name
        role_name = EVENT_ROLES.get(emoji_name)
        
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                member = guild.get_member(payload.user_id)
                if member:
                    try:
                        await member.add_roles(role)
                        logger.info(f"Assigned {role_name} to {member.display_name}")
                    except discord.Forbidden:
                        logger.error(f"Missing permissions to assign {role_name}")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to assign {role_name}: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.channel_id not in PING_CHANNEL_IDS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        emoji_name = payload.emoji.name
        role_name = EVENT_ROLES.get(emoji_name)
        
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                member = guild.get_member(payload.user_id)
                if member:
                    try:
                        await member.remove_roles(role)
                        logger.info(f"Removed {role_name} from {member.display_name}")
                    except discord.Forbidden:
                        logger.error(f"Missing permissions to remove {role_name}")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to remove {role_name}: {e}")

    @commands.command(name="setup_pings")
    @commands.has_permissions(administrator=True)
    async def setup_pings(self, ctx):
        """Creates the event ping reaction menu in the current channel."""
        if ctx.channel.id not in PING_CHANNEL_IDS:
            await ctx.send(f"⚠️ This channel ID ({ctx.channel.id}) is not listed in `PING_CHANNEL_IDS` in the `.env` file! The menu will deploy, but reactions won't assign roles until you add this channel ID to the config.")

        embed = discord.Embed(
            title="🔔 Event Ping Roles",
            description=(
                "React below to opt-in to automated event reminders!\n\n"
                "🐻 : **Bearhunt**\n"
                "⚔️ : **Arena**"
            ),
            color=discord.Color.blue()
        )
        msg = await ctx.send(embed=embed)
        
        # Seed the emojis
        for emoji in EVENT_ROLES.keys():
            await msg.add_reaction(emoji)

async def setup(bot):
    await bot.add_cog(Events(bot))
