import discord
from discord.ext import commands
from discord import app_commands
import logging
from services.database import get_all_ping_roles, set_ping_channel

logger = logging.getLogger(__name__)

class PingView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        
        self.roles_config = get_all_ping_roles()
        
        options = []
        for category, role_names in self.roles_config.items():
            for role_name in role_names:
                options.append(discord.SelectOption(
                    label=role_name,
                    description=f"{category} Ping",
                    value=role_name
                ))
                
        if not options:
            options.append(discord.SelectOption(label="No pings configured", value="none"))
            
        select = discord.ui.Select(
            placeholder="Select your ping roles...",
            min_values=0,
            max_values=len(options) if options[0].value != "none" else 1,
            options=options,
            custom_id="ping_role_select"
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def get_or_create_role(self, guild: discord.Guild, role_name: str) -> discord.Role | None:
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                role = await guild.create_role(name=role_name, mentionable=True, reason="Auto-created Ping Role")
            except Exception as e:
                logger.error(f"Failed to create role {role_name}: {e}")
                return None
        return role

    async def select_callback(self, interaction: discord.Interaction) -> None:
        if self.children[0].values and self.children[0].values[0] == "none":
            await interaction.response.send_message("No pings are configured.", ephemeral=True)
            return

        selected_roles_names = set(self.children[0].values)
        member = interaction.user
        guild = interaction.guild

        # Gather all possible ping role names
        all_ping_roles = set()
        for role_names in self.roles_config.values():
            all_ping_roles.update(role_names)

        roles_to_add = []
        roles_to_remove = []

        for role_name in all_ping_roles:
            role = await self.get_or_create_role(guild, role_name)
            if not role: continue
            
            if role_name in selected_roles_names:
                if role not in member.roles:
                    roles_to_add.append(role)
            else:
                if role in member.roles:
                    roles_to_remove.append(role)

        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Cannot add ping roles (missing permissions).", ephemeral=True)
                return
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Cannot remove ping roles (missing permissions).", ephemeral=True)
                return

        await interaction.response.send_message("✅ Your ping roles have been updated!", ephemeral=True)


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _has_officer_permission(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator:
            return True
        role_names = {r.name for r in member.roles}
        return "R4" in role_names or "R5" in role_names

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
        if not self._has_officer_permission(interaction.user):
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

        from services.database import add_ping_role
        try:
            add_ping_role(role_name, category)
            await interaction.response.send_message(f"✅ Created ping role **{role_name}** and linked it to category **{category}**.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error saving ping role to DB: {e}")
            await interaction.response.send_message(f"❌ Failed to save to database.", ephemeral=True)
            
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
