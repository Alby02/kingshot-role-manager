import discord
from discord.ext import commands
import os
import logging
from database import init_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bot')

class KingshotBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        await self.load_extension('cogs.roles')
        logger.info("Loaded extension: cogs.roles")
        await self.load_extension('cogs.verification')
        logger.info("Loaded extension: cogs.verification")
        
        # Sync slash commands globally
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} application commands.")
        except Exception as e:
            logger.error(f"Failed to sync application commands: {e}")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('Initializing SQLite Database...')
        init_db()
        logger.info('Initialization complete. Bot is ready.')

def main():
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set. Please provide it via .env file or environment.")
        return
        
    bot = KingshotBot()
    bot.run(token)

if __name__ == "__main__":
    main()
