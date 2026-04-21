import logging

import discord

from kingshot_role_manager.services.database import set_diplomat
from kingshot_role_manager.services.role_sync import sync_roles_for_user

logger = logging.getLogger(__name__)


class DiplomatConfirmView(discord.ui.View):
    def __init__(self, admin_id: int, game_id: str, ign: str, discord_id: int, is_adding: bool) -> None:
        super().__init__(timeout=60)
        self.admin_id = admin_id
        self.game_id = game_id
        self.ign = ign
        self.discord_id = discord_id
        self.is_adding = is_adding

    @discord.ui.button(label="Yes, confirm", style=discord.ButtonStyle.green, custom_id="dip_confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button["DiplomatConfirmView"]) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            set_diplomat(self.game_id, self.is_adding)
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
            await interaction.response.edit_message(view=self)

            action_str = "marked as **Diplomat**" if self.is_adding else "no longer a **Diplomat**"
            await interaction.followup.send(f"**{self.ign}** is {action_str}.", ephemeral=True)

            if self.discord_id and interaction.guild:
                await sync_roles_for_user(interaction.guild, self.discord_id)
        except Exception as exc:
            logger.error("Failed to change diplomat status: %s", exc)
            if not interaction.response.is_done():
                await interaction.response.send_message("Database error occurred.", ephemeral=True)
            else:
                await interaction.followup.send("Database error occurred.", ephemeral=True)

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="dip_confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button["DiplomatConfirmView"]) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(content="Action cancelled.", view=self)
