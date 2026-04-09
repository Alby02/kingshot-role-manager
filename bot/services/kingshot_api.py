import aiohttp
import logging

logger = logging.getLogger(__name__)

async def fetch_ign(player_id: str) -> str | None:
    """Fetch the IGN for a given Kingshot Player ID."""
    url = f"https://kingshot.net/api/player-info?playerId={player_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success" and "data" in data and "name" in data["data"]:
                        return data["data"]["name"]
        except Exception as e:
            logger.error(f"API Fetch Error: {e}")
    return None
