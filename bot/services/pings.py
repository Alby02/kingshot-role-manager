import os
import json
import logging

logger = logging.getLogger(__name__)

PINGS_FILE = "data/pings.json"

def get_pings_config() -> dict[str, dict]:
    try:
        if not os.path.exists(PINGS_FILE):
            os.makedirs(os.path.dirname(PINGS_FILE) or '.', exist_ok=True)
            default_pings = {
                "channels": {
                    "BOO": None,
                    "ZEN": None
                },
                "roles": {
                    "BOO": {
                        "🐻": "Bear1-BOO",
                        "🐼": "Bear2-BOO"
                    },
                    "ZEN": {
                        "🐻": "Bear1-ZEN",
                        "🐼": "Bear2-ZEN"
                    },
                    "BOTH": {
                        "⚔️": "Arena"
                    }
                }
            }
            with open(PINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_pings, f, indent=4, ensure_ascii=False)
            return default_pings
        
        with open(PINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure structure exists
            if "channels" not in data:
                data["channels"] = {"BOO": None, "ZEN": None}
            if "roles" not in data:
                # Migrate old format if needed
                if "BOO" in data and "roles" not in data:
                    roles = {
                        "BOO": data.pop("BOO", {}),
                        "ZEN": data.pop("ZEN", {}),
                        "BOTH": data.pop("BOTH", {})
                    }
                    data["roles"] = roles
            return data
    except Exception as e:
        logger.error(f"Failed to load pings.json: {e}")
        return {"channels": {"BOO": None, "ZEN": None}, "roles": {"BOO": {}, "ZEN": {}, "BOTH": {}}}

def save_pings_config(data: dict[str, dict]) -> None:
    os.makedirs(os.path.dirname(PINGS_FILE) or '.', exist_ok=True)
    with open(PINGS_FILE, 'w', encoding='utf-8') as f:
         json.dump(data, f, indent=4, ensure_ascii=False)

def set_ping_channel(alliance: str, channel_id: str) -> None:
    data = get_pings_config()
    data["channels"][alliance] = str(channel_id)
    save_pings_config(data)

def get_ping_channel(alliance: str) -> str | None:
    data = get_pings_config()
    return data["channels"].get(alliance)
