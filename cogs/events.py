import discord
from discord.ext import commands
import logging
import os
import json

logger = logging.getLogger(__name__)

# Load PING_CHANNEL_IDS from environment, expecting a comma-separated list of IDs
ping_channels_str = os.environ.get("PING_CHANNEL_IDS", "")
PING_CHANNEL_IDS = [int(cid.strip()) for cid in ping_channels_str.split(',') if cid.strip().isdigit()]

PINGS_FILE = "data/pings.json"

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_roles = self.load_pings()

    def load_pings(self):
        try:
            if not os.path.exists(PINGS_FILE):
                os.makedirs(os.path.dirname(PINGS_FILE) or '.', exist_ok=True)
                default_pings = {
                    "BOO": {
                        "🐻": "Bear1-BOO",
                        "⚔️": "Arena-BOO"
                    },
                    "ZEN": {
                        "🐼": "Bear1-ZEN",
                        "🛡️": "Arena-ZEN"
                    },
                    "BOTH": {
                        "📢": "All-Ping"
                    }
                }
                with open(PINGS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_pings, f, indent=4, ensure_ascii=False)
                return default_pings
            
            with open(PINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure the 3 base categories exist even if manually edited
                for cat in ["BOO", "ZEN", "BOTH"]:
                    if cat not in data:
                        data[cat] = {}
                return data
        except Exception as e:
            logger.error(f"Failed to load pings.json: {e}")
            return {"BOO": {}, "ZEN": {}, "BOTH": {}}

    async def get_or_create_role(self, guild, role_name):
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                role = await guild.create_role(name=role_name, mentionable=True, reason="Auto-created Ping Role")
                logger.info(f"Auto-created missing role: {role_name}")
            except Exception as e:
                logger.error(f"Failed to create role {role_name}: {e}")
                return None
        return role

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
        role_name = None
        for category, roles in self.event_roles.items():
            if emoji_name in roles:
                role_name = roles[emoji_name]
                break
        
        if role_name:
            role = await self.get_or_create_role(guild, role_name)
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
        role_name = None
        for category, roles in self.event_roles.items():
            if emoji_name in roles:
                role_name = roles[emoji_name]
                break
        
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

        description = "React below to opt-in to automated event reminders!\n\n"
        
        for category, roles in self.event_roles.items():
            if roles:
                description += f"**{category} Events**\n"
                for emoji, role_name in roles.items():
                    description += f"{emoji} : {role_name}\n"
                description += "\n"

        embed = discord.Embed(
            title="🔔 Event Ping Roles",
            description=description.strip(),
            color=discord.Color.blue()
        )
        msg = await ctx.send(embed=embed)
        
        # Seed the emojis
        for category, roles in self.event_roles.items():
            for emoji in roles.keys():
                try:
                    await msg.add_reaction(emoji)
                except discord.HTTPException:
                    logger.warning(f"Failed to add reaction emoji: {emoji}")

    @commands.command(name="syncPings")
    @commands.has_permissions(administrator=True)
    async def sync_pings(self, ctx):
        """Reloads the event ping configuration from data/pings.json"""
        self.event_roles = self.load_pings()
        
        count = sum(len(roles) for roles in self.event_roles.values())
        await ctx.send(f"✅ Successfully reloaded {count} ping roles across {len(self.event_roles)} categories from `data/pings.json`!")

async def setup(bot):
    await bot.add_cog(Events(bot))
