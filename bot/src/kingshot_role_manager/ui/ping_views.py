import logging

import discord

from kingshot_role_manager.services.database import get_all_ping_roles
from kingshot_role_manager.services.permissions import ensure_role_exists

logger = logging.getLogger(__name__)


class PingRoleSelect(discord.ui.Select["PingView"]):
    def __init__(self, options: list[discord.SelectOption]) -> None:
        super().__init__(
            placeholder="Select your ping roles...",
            min_values=0,
            max_values=len(options) if options[0].value != "none" else 1,
            options=options,
            custom_id="ping_role_select",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is None:
            await interaction.response.send_message("View is not available.", ephemeral=True)
            return
        await self.view.handle_select(interaction, self.values)


class PingView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

        self.roles_config = get_all_ping_roles()

        options = []
        for category, role_names in self.roles_config.items():
            for role_name in role_names:
                options.append(
                    discord.SelectOption(
                        label=role_name,
                        description=f"{category} ping",
                        value=role_name,
                    )
                )

        if not options:
            options.append(discord.SelectOption(label="No pings configured", value="none"))

        select = PingRoleSelect(options)
        self.add_item(select)

    async def handle_select(self, interaction: discord.Interaction, selected_values: list[str]) -> None:
        if selected_values and selected_values[0] == "none":
            await interaction.response.send_message("No pings are configured.", ephemeral=True)
            return

        selected_roles_names = set(selected_values)
        member = interaction.user
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Could not resolve your server member record.", ephemeral=True)
            return

        all_ping_roles = set()
        for role_names in self.roles_config.values():
            all_ping_roles.update(role_names)

        roles_to_add = []
        roles_to_remove = []

        for role_name in all_ping_roles:
            role = await ensure_role_exists(guild, role_name, mentionable=True, reason="Auto-created ping role")
            if not role:
                logger.warning("Skipping ping role '%s' because it could not be created.", role_name)
                continue

            if role_name in selected_roles_names:
                if role not in member.roles:
                    roles_to_add.append(role)
            elif role in member.roles:
                roles_to_remove.append(role)

        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add)
            except discord.Forbidden:
                await interaction.response.send_message("Cannot add ping roles (missing permissions).", ephemeral=True)
                return

        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove)
            except discord.Forbidden:
                await interaction.response.send_message("Cannot remove ping roles (missing permissions).", ephemeral=True)
                return

        await interaction.response.send_message("Your ping roles have been updated.", ephemeral=True)
