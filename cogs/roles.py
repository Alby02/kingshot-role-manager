import discord
from discord.ext import commands
import os
import logging

logger = logging.getLogger(__name__)

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji_to_role = {
            "🟢": "Guest",
            "🤝": "Diplomat",
            "⚔️": "Member-Verification"
        }

    @commands.Cog.listener()
    async def on_ready(self):
        channel_id = os.environ.get('RULES_CHANNEL_ID')
        message_id = os.environ.get('RULES_MESSAGE_ID')
        
        if not channel_id or not message_id:
            logger.warning("RULES_CHANNEL_ID or RULES_MESSAGE_ID is missing from .env. Auto-react feature disabled.")
            return

        try:
            channel = self.bot.get_channel(int(channel_id)) or await self.bot.fetch_channel(int(channel_id))
            message = await channel.fetch_message(int(message_id))
            for emoji in self.emoji_to_role.keys():
                await message.add_reaction(emoji)
            logger.info("Successfully added default reaction emojis to the rules message.")
        except Exception as e:
            logger.error(f"Failed to auto-react to rules message: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        message_id = os.environ.get('RULES_MESSAGE_ID')
        if not message_id or payload.message_id != int(message_id):
            return

        role_name = self.emoji_to_role.get(str(payload.emoji))
        if not role_name:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            logger.warning(f"Role '{role_name}' not found in the server. Please create it.")
            return

        member = payload.member
        if member:
            try:
                await member.add_roles(role)
                logger.info(f"Assigned role {role_name} to {member.display_name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to add role {role_name} to {member.display_name}")
            except discord.HTTPException as e:
                logger.error(f"Failed to add role {role_name}: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        message_id = os.environ.get('RULES_MESSAGE_ID')
        if not message_id or payload.message_id != int(message_id):
            return

        role_name = self.emoji_to_role.get(str(payload.emoji))
        if not role_name:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            return

        member = guild.get_member(payload.user_id)
        if member:
            try:
                await member.remove_roles(role)
                logger.info(f"Removed role {role_name} from {member.display_name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to remove role {role_name} from {member.display_name}")
            except discord.HTTPException as e:
                logger.error(f"Failed to remove role {role_name}: {e}")

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
