import aiohttp
import logging
from typing import TypedDict

logger = logging.getLogger(__name__)


class KingshotPlayerData(TypedDict):
    name: str
    kingdom: int
    level: int
    profilePhoto: str | None

async def fetch_ign(player_id: str) -> KingshotPlayerData | None:
    """Fetch the IGN and profile photo for a given Kingshot Player ID."""
    url = f"https://kingshot.net/api/player-info?playerId={player_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success" and "data" in data and "name" in data["data"]:
                        return {
                            "name": data["data"]["name"],
                            "kingdom": data["data"].get("kingdom", 0),
                            "level": data["data"].get("level", 0),
                            "profilePhoto": data["data"].get("profilePhoto")
                        }
        except Exception as e:
            logger.error(f"API Fetch Error: {e}")
    return None
