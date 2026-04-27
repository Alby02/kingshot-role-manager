import logging
import discord

from kingshot_role_manager.services.database import register_user, set_diplomat
from kingshot_role_manager.services.role_sync import sync_roles_for_user

logger = logging.getLogger(__name__)

class BaseConfirmView(discord.ui.View):
    def __init__(self, authorized_user_id: int) -> None:
        super().__init__(timeout=60)
        self.authorized_user_id = authorized_user_id

    async def execute_action(self, interaction: discord.Interaction) -> None:
        """To be implemented by subclasses"""
        raise NotImplementedError

    @discord.ui.button(label="Yes, confirm", style=discord.ButtonStyle.green, custom_id="base_confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button["BaseConfirmView"]) -> None:
        if interaction.user.id != self.authorized_user_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        try:
            await self.execute_action(interaction)
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
            if not interaction.response.is_done():
                await interaction.response.edit_message(view=self)
            else:
                await interaction.edit_original_response(view=self)
        except Exception as exc:
            logger.error(f"Error during confirmation action: {exc}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred during confirmation.", ephemeral=True)
            else:
                await interaction.followup.send("An error occurred during confirmation.", ephemeral=True)

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.red, custom_id="base_confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button["BaseConfirmView"]) -> None:
        if interaction.user.id != self.authorized_user_id:
            await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
            return

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(content="Action cancelled.", view=self)


class LinkAccountView(BaseConfirmView):
    def __init__(self, actor_id: int, target_member_id: int, game_id: str, ign: str, kingdom: int, level: int) -> None:
        super().__init__(authorized_user_id=actor_id)
        self.target_member_id = target_member_id
        self.game_id = game_id
        self.ign = ign
        self.kingdom = kingdom
        self.level = level

    async def execute_action(self, interaction: discord.Interaction) -> None:
        register_user(self.target_member_id, self.game_id, self.ign, self.kingdom, self.level)
        await interaction.response.edit_message(view=self)
        
        target_mention = f"<@{self.target_member_id}>" if self.authorized_user_id != self.target_member_id else "your account"
        await interaction.followup.send(f"Success! Linked account **{self.ign}** to {target_mention}.", ephemeral=True)
        
        if interaction.guild:
            await sync_roles_for_user(interaction.guild, self.target_member_id)


class DiplomatActionView(BaseConfirmView):
    def __init__(self, actor_id: int, game_id: str, ign: str, target_member_id: int, is_adding: bool) -> None:
        super().__init__(authorized_user_id=actor_id)
        self.game_id = game_id
        self.ign = ign
        self.target_member_id = target_member_id
        self.is_adding = is_adding

    async def execute_action(self, interaction: discord.Interaction) -> None:
        set_diplomat(self.game_id, self.is_adding)
        await interaction.response.edit_message(view=self)
        
        action_str = "marked as **Diplomat**" if self.is_adding else "no longer a **Diplomat**"
        await interaction.followup.send(f"**{self.ign}** is {action_str}.", ephemeral=True)

        if self.target_member_id and interaction.guild:
            await sync_roles_for_user(interaction.guild, self.target_member_id)
