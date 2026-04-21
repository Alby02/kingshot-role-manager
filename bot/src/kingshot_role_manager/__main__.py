import logging
import os

import discord
from discord.ext import commands

from kingshot_role_manager.services.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bot")


class KingshotBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        extensions = [
            "kingshot_role_manager.cogs.verification",
            "kingshot_role_manager.cogs.events",
            "kingshot_role_manager.cogs.admin",
            "kingshot_role_manager.cogs.diplomacy",
            "kingshot_role_manager.cogs.reconciliation",
        ]
        for extension in extensions:
            await self.load_extension(extension)
            logger.info("Loaded extension: %s", extension)

        await self.tree.sync()
        logger.info("Synced app commands globally.")

    async def on_ready(self) -> None:
        if self.user:
            logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        logger.info("Initializing PostgreSQL schema...")
        init_db()
        logger.info("Initialization complete. Bot is ready.")


def main() -> None:
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set.")
        return

    bot = KingshotBot()
    bot.run(token)


if __name__ == "__main__":
    main()
