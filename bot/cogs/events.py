import discord
from discord.ext import commands
import logging
import os
import json

logger = logging.getLogger(__name__)

# Load Ping channel IDs from environment
ping_boo = os.environ.get("PING_CHANNEL_BOO_ID", "")
ping_zen = os.environ.get("PING_CHANNEL_ZEN_ID", "")
PING_CHANNEL_IDS = [int(cid.strip()) for cid in [ping_boo, ping_zen] if cid.strip().isdigit()]

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
                        "🐼": "Bear2-BOO"
                    },
                    "ZEN": {
                        "🐻": "Bear1-ZEN",
                        "🐼": "Bear2-ZEN"
                    },
                    "BOTH": {
                        "⚔️": "Arena"
                    }
                }
                with open(PINGS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_pings, f, indent=4, ensure_ascii=False)
                return default_pings
            
            with open(PINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
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

    def get_role_from_payload(self, emoji_name, channel_id):
        is_boo = str(channel_id) == str(ping_boo)
        is_zen = str(channel_id) == str(ping_zen)
        
        categories_to_check = ["BOTH"]
        if is_boo:
            categories_to_check.insert(0, "BOO")
        elif is_zen:
            categories_to_check.insert(0, "ZEN")

        for category in categories_to_check:
            roles = self.event_roles.get(category, {})
            if emoji_name in roles:
                return roles[emoji_name]
        return None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.channel_id not in PING_CHANNEL_IDS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role_name = self.get_role_from_payload(payload.emoji.name, payload.channel_id)
        
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

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.channel_id not in PING_CHANNEL_IDS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role_name = self.get_role_from_payload(payload.emoji.name, payload.channel_id)
        
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

    @commands.command(name="setup_pings")
    @commands.has_permissions(administrator=True)
    async def setup_pings(self, ctx):
        """Creates the event ping reaction menu in the current channel."""
        channel_id = str(ctx.channel.id)
        is_boo = channel_id == str(ping_boo)
        is_zen = channel_id == str(ping_zen)

        if not is_boo and not is_zen:
            await ctx.send(f"⚠️ This channel ID ({channel_id}) is neither PING_CHANNEL_BOO_ID nor PING_CHANNEL_ZEN_ID in the `.env` file! Setup aborted.")
            return

        description = "React below to opt-in to automated event reminders!\n\n"
        
        categories_to_show = ["BOTH"]
        if is_boo:
            categories_to_show.insert(0, "BOO")
        elif is_zen:
            categories_to_show.insert(0, "ZEN")

        emojis_to_seed = []

        for category in categories_to_show:
            roles = self.event_roles.get(category, {})
            if roles:
                description += f"**{category} Events**\n"
                for emoji, role_name in roles.items():
                    description += f"{emoji} : {role_name}\n"
                    emojis_to_seed.append(emoji)
                description += "\n"

        embed = discord.Embed(
            title="🔔 Event Ping Roles",
            description=description.strip(),
            color=discord.Color.blue()
        )
        msg = await ctx.send(embed=embed)
        
        # Seed the emojis
        for emoji in emojis_to_seed:
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
