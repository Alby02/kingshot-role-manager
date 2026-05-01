# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from curl_cffi.requests import AsyncSession
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
    
    # Use curl_cffi to spoof Chrome's TLS fingerprint and bypass WAF. 
    # It automatically generates the correct User-Agent for the impersonated browser!
    async with AsyncSession(impersonate="chrome") as session:
        try:
            response = await session.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data and "name" in data["data"]:
                    return {
                        "name": data["data"]["name"],
                        "kingdom": data["data"].get("kingdom", 0),
                        "level": data["data"].get("level", 0),
                        "profilePhoto": data["data"].get("profilePhoto")
                    }
                else:
                    logger.warning(f"API returned 200 OK but with unexpected JSON structure: {data}")
            else:
                text = response.text
                logger.warning(f"API returned non-200 status code {response.status_code}: {text[:300]}")
        except Exception as e:
            logger.error(f"API Fetch Error: {e}")
    return None
