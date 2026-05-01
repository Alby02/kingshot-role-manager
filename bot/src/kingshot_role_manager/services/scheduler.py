import asyncio
import logging
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import commands

from kingshot_role_manager.services.database import (
    get_all_ping_schedules, 
    ScheduledPing, 
    delete_ping_schedule, 
    update_ping_schedule_time, 
    get_all_ping_roles, 
    get_ping_channel
)

from typing import Any

logger = logging.getLogger(__name__)

class PingTimerService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task: asyncio.Task[Any] | None = None
        self.start()

    def start(self):
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = self.bot.loop.create_task(self._run())

    async def _run(self):
        try:
            while True:
                schedules = get_all_ping_schedules()
                if not schedules:
                    # Nothing to schedule, sleep for a long time. 
                    # wake_up() will cancel this sleep if a new schedule is added.
                    await asyncio.sleep(3600)
                    continue

                next_ping = schedules[0]
                now = datetime.now(timezone.utc)
                
                if next_ping["send_at"] <= now:
                    await self._execute_ping(next_ping)
                else:
                    await discord.utils.sleep_until(next_ping["send_at"])
                    await self._execute_ping(next_ping)
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in TimerService: {e}")
            await asyncio.sleep(10)
            self.start()

    def wake_up(self):
        """Called when a new ping is added to force the loop to recalculate immediately."""
        self.start()

    async def _execute_ping(self, schedule: ScheduledPing):
        roles_config = get_all_ping_roles()
        category = None
        for cat, roles in roles_config.items():
            if schedule["role_name"] in roles:
                category = cat
                break
                
        if not category:
            logger.error(f"Could not find category for role {schedule['role_name']}. Skipping ping.")
            delete_ping_schedule(schedule["id"])
            return

        channel_id_str = get_ping_channel(category)
        if not channel_id_str:
            logger.error(f"No channel configured for category {category}. Skipping ping.")
            delete_ping_schedule(schedule["id"])
            return

        channel = self.bot.get_channel(int(channel_id_str))
        if isinstance(channel, discord.TextChannel):
            role_mention = f"@{schedule['role_name']}"
            guild = channel.guild
            role = discord.utils.get(guild.roles, name=schedule['role_name'])
            if role:
                role_mention = role.mention
                
            try:
                await channel.send(f"{role_mention}\n\n{schedule['message']}")
            except Exception as e:
                logger.error(f"Failed to send scheduled ping: {e}")
        else:
            logger.error(f"Channel {channel_id_str} is not a valid text channel.")

        rec = schedule["recurrence"]
        if rec and rec.startswith("R:"):
            parts = rec.split(":")
            if len(parts) == 5:
                try:
                    h, d, w, m = map(int, parts[1:])
                    next_time = schedule["send_at"] + timedelta(hours=h, days=d, weeks=w)
                    if m > 0:
                        new_month = next_time.month - 1 + m
                        new_year = next_time.year + new_month // 12
                        new_month = new_month % 12 + 1
                        
                        import calendar
                        max_day = calendar.monthrange(new_year, new_month)[1]
                        new_day = min(next_time.day, max_day)
                        
                        next_time = next_time.replace(year=new_year, month=new_month, day=new_day)
                        
                    update_ping_schedule_time(schedule["id"], next_time)
                except ValueError:
                    logger.error(f"Invalid recurrence format for schedule {schedule['id']}: {rec}")
                    delete_ping_schedule(schedule["id"])
            else:
                delete_ping_schedule(schedule["id"])
        else:
            delete_ping_schedule(schedule["id"])
