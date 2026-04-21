import logging

import discord

from kingshot_role_manager.services.database import register_user
from kingshot_role_manager.services.role_sync import sync_roles_for_user

logger = logging.getLogger(__name__)


class ConfirmView(discord.ui.View):
    def __init__(self, discord_id: int, game_id: str, ign: str, kingdom: int, level: int) -> None:
        super().__init__(timeout=60)
        self.discord_id = discord_id
        self.game_id = game_id
        self.ign = ign
        self.kingdom = kingdom
        self.level = level

    @discord.ui.button(label="Yes, this is me", style=discord.ButtonStyle.green, custom_id="confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button["ConfirmView"]) -> None:
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            register_user(self.discord_id, self.game_id, self.ign, self.kingdom, self.level)

            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
            await interaction.response.edit_message(view=self)

            await interaction.followup.send(f"Success! Your account **{self.ign}** has been linked.", ephemeral=True)

            if interaction.guild:
                await sync_roles_for_user(interaction.guild, self.discord_id)

        except Exception as exc:
            logger.error("DB error during verify confirmation: %s", exc)
            if not interaction.response.is_done():
                await interaction.response.send_message("Database error occurred while linking your account.", ephemeral=True)
            else:
                await interaction.followup.send("Database error occurred while linking your account.", ephemeral=True)

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button["ConfirmView"]) -> None:
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(content="Verification cancelled.", view=self)


class SetPlayerConfirmView(discord.ui.View):
    def __init__(self, admin_id: int, target_member: discord.Member, game_id: str, ign: str, kingdom: int, level: int) -> None:
        super().__init__(timeout=60)
        self.admin_id = admin_id
        self.target_member = target_member
        self.game_id = game_id
        self.ign = ign
        self.kingdom = kingdom
        self.level = level

    @discord.ui.button(label="Yes, assign it", style=discord.ButtonStyle.green, custom_id="admin_confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button["SetPlayerConfirmView"]) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            register_user(self.target_member.id, self.game_id, self.ign, self.kingdom, self.level)
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                f"Success! Linked account **{self.ign}** to {self.target_member.mention}.",
                ephemeral=True,
            )
            if interaction.guild:
                await sync_roles_for_user(interaction.guild, self.target_member.id)
        except Exception as exc:
            logger.error("Failed to force-set player: %s", exc)
            if not interaction.response.is_done():
                await interaction.response.send_message("Database error occurred while forcing assignment.", ephemeral=True)
            else:
                await interaction.followup.send("Database error occurred while forcing assignment.", ephemeral=True)

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="admin_confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button["SetPlayerConfirmView"]) -> None:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(content="Setplayer cancelled.", view=self)
