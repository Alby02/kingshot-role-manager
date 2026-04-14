import discord
from discord.ext import commands
import os
import logging
from services.database import init_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bot')

class KingshotBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self) -> None:
        await self.load_extension('cogs.verification')
        logger.info("Loaded extension: cogs.verification")
        await self.load_extension('cogs.events')
        logger.info("Loaded extension: cogs.events")
        await self.load_extension('cogs.admin')
        logger.info("Loaded extension: cogs.admin")
        await self.load_extension('cogs.reconciliation')
        logger.info("Loaded extension: cogs.reconciliation")
        await self.tree.sync()
        logger.info("Synced app commands globally.")

    async def on_ready(self) -> None:
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('Initializing PostgreSQL schema...')
        init_db()
        logger.info('Initialization complete. Bot is ready.')

def main() -> None:
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set. Please provide it via .env file or environment.")
        return
        
    bot = KingshotBot()
    bot.run(token)

if __name__ == "__main__":
    main()
