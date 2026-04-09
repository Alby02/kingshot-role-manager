import discord
from discord.ext import commands
from discord import app_commands
import logging
from services.pings import get_pings_config, set_ping_channel

logger = logging.getLogger(__name__)

class PingView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        
        config = get_pings_config()
        self.roles_config = config.get("roles", {})
        
        # Build one select menu if we have categories, or multiple. A single select is easiest.
        options = []
        for category, emoji_map in self.roles_config.items():
            for emoji, role_name in emoji_map.items():
                options.append(discord.SelectOption(
                    label=role_name,
                    description=f"{category} Ping",
                    emoji=emoji,
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
        for emoji_map in self.roles_config.values():
            all_ping_roles.update(emoji_map.values())

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

    @app_commands.command(name="pings", description="Manage your event ping roles privately.")
    async def pings(self, interaction: discord.Interaction) -> None:
        view = PingView()
        await interaction.response.send_message("Select the event pings you want to be notified for:", view=view, ephemeral=True)

    @app_commands.command(name="set_ping_channel", description="Set the dedicated announcement channel for a specific alliance.")
    @app_commands.describe(alliance="The alliance (BOO or ZEN)", channel="The channel for announcements")
    @app_commands.default_permissions(administrator=True)
    async def set_ping_channel_cmd(self, interaction: discord.Interaction, alliance: str, channel: discord.TextChannel) -> None:
        alliance = alliance.upper()
        if alliance not in ["BOO", "ZEN"]:
            await interaction.response.send_message("❌ Alliance must be BOO or ZEN.", ephemeral=True)
            return
            
        set_ping_channel(alliance, str(channel.id))
        await interaction.response.send_message(f"✅ Set **{alliance}** event pings to output in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="sync_pings", description="Reloads the event ping configuration from data/pings.json")
    @app_commands.default_permissions(administrator=True)
    async def sync_pings(self, interaction: discord.Interaction) -> None:
        # We don't cache locally in the cog anymore, so reading it again validates the file.
        config = get_pings_config()
        count = sum(len(roles) for roles in config.get("roles", {}).values())
        await interaction.response.send_message(f"✅ Validated pings file. Detected {count} ping roles.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
