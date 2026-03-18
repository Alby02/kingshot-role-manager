import discord
import os
import logging
from database import init_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('bot')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logger.info('Initializing SQLite Database...')
    init_db()
    logger.info('Initialization complete. Bot is ready.')

def main():
    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set. Please provide it via .env file or environment.")
        return
    bot.run(token)

if __name__ == "__main__":
    main()
