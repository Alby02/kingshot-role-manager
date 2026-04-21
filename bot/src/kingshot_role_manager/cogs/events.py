import discord
from discord.ext import commands
from discord import app_commands
import logging
from kingshot_role_manager.services.database import set_ping_channel, add_ping_role
from kingshot_role_manager.services.permissions import has_officer_permission
from kingshot_role_manager.ui.ping_views import PingView

logger = logging.getLogger(__name__)


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="pings", description="Manage your event ping roles privately.")
    async def pings(self, interaction: discord.Interaction) -> None:
        view = PingView()
        await interaction.response.send_message("Select the event pings you want to be notified for:", view=view, ephemeral=True)

    @app_commands.command(name="set_ping_channel", description="Set the dedicated announcement channel for a specific category.")
    @app_commands.describe(category="The ping category (e.g. BOO, ZEN, BOTH)", channel="The channel for announcements")
    @app_commands.default_permissions(administrator=True)
    async def set_ping_channel_cmd(self, interaction: discord.Interaction, category: str, channel: discord.TextChannel) -> None:
        category = category.upper()
            
        set_ping_channel(category, str(channel.id))
        await interaction.response.send_message(f"✅ Set **{category}** event pings to output in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="create_ping", description="Create a new ping role and assign it to a category (R4/R5/Admin).")
    @app_commands.describe(category="The category the ping belongs to", role_name="The exact name of the role to create/assign")
    @app_commands.default_permissions(administrator=True)
    async def create_ping_role(self, interaction: discord.Interaction, category: str, role_name: str) -> None:
        if not isinstance(interaction.user, discord.Member) or not has_officer_permission(interaction.user):
            await interaction.response.send_message("❌ Only **R4**, **R5**, or **Administrators** can use this command.", ephemeral=True)
            return

        category = category.upper()
        
        # Try to create the role on the server if it doesn't exist
        guild = interaction.guild
        if guild:
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    await guild.create_role(name=role_name, mentionable=True, reason=f"Created via /create_ping by {interaction.user.display_name}")
                except Exception as e:
                    await interaction.response.send_message(f"❌ Failed to create discord role: {e}", ephemeral=True)
                    return

        try:
            add_ping_role(role_name, category)
            await interaction.response.send_message(f"✅ Created ping role **{role_name}** and linked it to category **{category}**.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error saving ping role to DB: {e}")
            await interaction.response.send_message(f"❌ Failed to save to database.", ephemeral=True)
            
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
