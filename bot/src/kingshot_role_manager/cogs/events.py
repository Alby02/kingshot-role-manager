import discord
from discord.ext import commands
from discord import app_commands
import logging
from kingshot_role_manager.services.database import set_ping_channel, add_ping_role
from kingshot_role_manager.services.permissions import has_officer_permission
from kingshot_role_manager.ui.ping_views import PingView
from kingshot_role_manager.services.scheduler import PingTimerService
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.timer_service = PingTimerService(bot)

    @app_commands.command(name="pings", description="Manage your event ping roles privately.")
    async def pings(self, interaction: discord.Interaction) -> None:
        from kingshot_role_manager.services.database import get_discord_user_roles
        roles_data = get_discord_user_roles(interaction.user.id)
        user_alliances = roles_data["alliances"]

        view = PingView(user_alliances)
        await interaction.response.send_message("Select the event pings you want to be notified for:", view=view, ephemeral=True)

    @app_commands.command(name="ping_config", description="View all ping categories and channels configuration.")
    @app_commands.default_permissions(administrator=True)
    async def ping_config(self, interaction: discord.Interaction) -> None:
        from kingshot_role_manager.services.database import get_all_ping_roles, get_ping_channel
        
        roles_config = get_all_ping_roles()
        if not roles_config:
            await interaction.response.send_message("No ping categories configured yet.", ephemeral=True)
            return

        embed = discord.Embed(title="Ping Configuration", color=discord.Color.blue())
        for category, roles in roles_config.items():
            channel_id = get_ping_channel(category)
            channel_str = f"<#{channel_id}>" if channel_id else "None"
            roles_str = ", ".join([f"`{r}`" for r in roles]) if roles else "No roles"
            
            embed.add_field(name=f"Category: {category}", value=f"**Channel:** {channel_str}\n**Roles:** {roles_str}", inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

    @app_commands.command(name="schedule_ping", description="Schedule an automatic ping message.")
    @app_commands.describe(
        role_name="The exact name of the ping role",
        message="The message to send",
        time_str="When to send in UTC (format: YYYY-MM-DD HH:MM)",
        recurrence="Optional: format R:HH:DD:WW:MM (e.g. R:0:2:0:0 for every 2 days)"
    )
    @app_commands.default_permissions(administrator=True)
    async def schedule_ping(
        self, 
        interaction: discord.Interaction, 
        role_name: str, 
        message: str, 
        time_str: str,
        recurrence: str | None = None
    ) -> None:
        try:
            send_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            await interaction.response.send_message("❌ Invalid time format. Please use `YYYY-MM-DD HH:MM` (e.g. `2026-05-05 18:00`).", ephemeral=True)
            return

        rec_val = None
        if recurrence:
            rec_clean = recurrence.strip(":").upper()
            parts = rec_clean.split(":")
            if len(parts) == 5 and parts[0] == "R":
                try:
                    _ = list(map(int, parts[1:]))
                    rec_val = rec_clean
                except ValueError:
                    await interaction.response.send_message("❌ Invalid recurrence format. Must be `R:HH:DD:WW:MM` with integers.", ephemeral=True)
                    return
            else:
                await interaction.response.send_message("❌ Invalid recurrence format. Must be `R:HH:DD:WW:MM`.", ephemeral=True)
                return

        from kingshot_role_manager.services.database import add_ping_schedule
        try:
            add_ping_schedule(role_name, message, send_at, rec_val)
            self.timer_service.wake_up()
            rec_str = f" ({recurrence})" if rec_val else ""
            await interaction.response.send_message(f"✅ Scheduled ping for **{role_name}** at {send_at.strftime('%Y-%m-%d %H:%M UTC')}{rec_str}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to schedule ping: {e}", ephemeral=True)
            
    @app_commands.command(name="schedules", description="List all scheduled pings.")
    @app_commands.default_permissions(administrator=True)
    async def list_schedules(self, interaction: discord.Interaction) -> None:
        from kingshot_role_manager.services.database import get_all_ping_schedules
        schedules = get_all_ping_schedules()
        if not schedules:
            await interaction.response.send_message("There are no scheduled pings.", ephemeral=True)
            return

        embed = discord.Embed(title="Scheduled Pings", color=discord.Color.green())
        for sched in schedules:
            rec = sched['recurrence'] or 'Once'
            embed.add_field(
                name=f"ID: {sched['id']} | Role: {sched['role_name']}",
                value=f"**Time:** {sched['send_at'].strftime('%Y-%m-%d %H:%M UTC')}\n**Recurrence:** {rec}\n**Message:** {sched['message'][:50]}...",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delete_schedule", description="Delete a scheduled ping by ID.")
    @app_commands.describe(schedule_id="The ID of the schedule to delete (use /schedules to find it)")
    @app_commands.default_permissions(administrator=True)
    async def delete_schedule_cmd(self, interaction: discord.Interaction, schedule_id: int) -> None:
        from kingshot_role_manager.services.database import delete_ping_schedule, get_ping_schedule
        sched = get_ping_schedule(schedule_id)
        if not sched:
            await interaction.response.send_message(f"❌ Schedule ID {schedule_id} not found.", ephemeral=True)
            return
        try:
            delete_ping_schedule(schedule_id)
            self.timer_service.wake_up()
            await interaction.response.send_message(f"✅ Deleted schedule ID {schedule_id} (Role: {sched['role_name']}).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to delete schedule: {e}", ephemeral=True)

    @app_commands.command(name="edit_schedule", description="Edit an existing scheduled ping.")
    @app_commands.describe(
        schedule_id="The ID of the schedule to edit",
        role_name="New role name (optional)",
        message="New message (optional)",
        time_str="New time in UTC YYYY-MM-DD HH:MM (optional)",
        recurrence="New recurrence format R:HH:DD:WW:MM or 'None' to clear"
    )
    @app_commands.default_permissions(administrator=True)
    async def edit_schedule(
        self,
        interaction: discord.Interaction,
        schedule_id: int,
        role_name: str | None = None,
        message: str | None = None,
        time_str: str | None = None,
        recurrence: str | None = None
    ) -> None:
        from kingshot_role_manager.services.database import get_ping_schedule, update_ping_schedule_full
        sched = get_ping_schedule(schedule_id)
        if not sched:
            await interaction.response.send_message(f"❌ Schedule ID {schedule_id} not found.", ephemeral=True)
            return

        new_role = role_name if role_name else sched['role_name']
        new_msg = message if message else sched['message']
        
        new_rec = sched['recurrence']
        if recurrence:
            if recurrence.lower() == "none":
                new_rec = None
            else:
                rec_clean = recurrence.strip(":").upper()
                parts = rec_clean.split(":")
                if len(parts) == 5 and parts[0] == "R":
                    try:
                        _ = list(map(int, parts[1:]))
                        new_rec = rec_clean
                    except ValueError:
                        await interaction.response.send_message("❌ Invalid recurrence format. Must be `R:HH:DD:WW:MM` with integers.", ephemeral=True)
                        return
                else:
                    await interaction.response.send_message("❌ Invalid recurrence format. Must be `R:HH:DD:WW:MM`.", ephemeral=True)
                    return

        new_send_at = sched['send_at']
        if time_str:
            try:
                new_send_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            except ValueError:
                await interaction.response.send_message("❌ Invalid time format. Please use `YYYY-MM-DD HH:MM`.", ephemeral=True)
                return

        try:
            update_ping_schedule_full(schedule_id, new_role, new_msg, new_send_at, new_rec)
            self.timer_service.wake_up()
            await interaction.response.send_message(f"✅ Successfully updated schedule ID {schedule_id}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to update schedule: {e}", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
