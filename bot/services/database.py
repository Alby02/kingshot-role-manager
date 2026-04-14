import os
import logging
import psycopg

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/kingshot_role_manager",
)


def get_connection() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)


SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS players (
    game_id TEXT PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    ign TEXT NOT NULL,
    kingdom INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    is_diplomat BOOLEAN NOT NULL DEFAULT FALSE,
    has_been_in_alliance BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS roster (
    ign TEXT PRIMARY KEY,
    alliance TEXT NOT NULL,
    rank TEXT NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS ping_channels (
    category TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ping_roles (
    role_name TEXT PRIMARY KEY,
    category TEXT NOT NULL
);
'''

def init_db() -> None:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(SCHEMA_SQL)

        conn.commit()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# ---------------------------------------------------------------------------
# Player Registration
# ---------------------------------------------------------------------------

def register_user(discord_id: int, game_id: str, ign: str, kingdom: int = 0, level: int = 0) -> None:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if ign is in roster
        cursor.execute("SELECT 1 FROM roster WHERE ign = %s", (ign,))
        in_roster = cursor.fetchone() is not None

        # We need to preserve has_been_in_alliance/is_diplomat if it exists
        cursor.execute('SELECT is_diplomat, has_been_in_alliance FROM players WHERE game_id = %s', (game_id,))
        row = cursor.fetchone()
        
        has_been = 1 if in_roster else 0
        
        if row:
            if row[1]: # preserve if already true
                has_been = 1
            cursor.execute('''
                UPDATE players
                SET discord_id = %s, ign = %s, kingdom = %s, level = %s, has_been_in_alliance = %s
                WHERE game_id = %s
            ''', (discord_id, ign, kingdom, level, bool(has_been), game_id))
        else:
            cursor.execute('''
                INSERT INTO players (game_id, discord_id, ign, kingdom, level, has_been_in_alliance) 
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (game_id, discord_id, ign, kingdom, level, bool(has_been)))

        conn.commit()
    except Exception as e:
        logger.error(f"Error registering user in DB: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def update_player_data(discord_id: int, game_id: str, ign: str, kingdom: int, level: int) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT discord_id FROM players WHERE game_id = %s', (game_id,))
        row = cursor.fetchone()
        if not row or row[0] != discord_id:
            return False

        cursor.execute('UPDATE players SET ign = %s, kingdom = %s, level = %s WHERE game_id = %s', (ign, kingdom, level, game_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating IGN in DB: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_user_igns(discord_id: int) -> list[tuple]:
    """Return all game accounts linked to a Discord user with their current roster status."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.game_id, p.ign, r.alliance, r.rank, p.is_diplomat, p.kingdom, p.level 
            FROM players p
            LEFT JOIN roster r ON p.ign = r.ign
            WHERE p.discord_id = %s
        ''', (discord_id,))
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching IGNs: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_discord_user_roles(discord_id: int) -> dict[str, set[str] | bool]:
    """
    Aggregate role-relevant info for a Discord user across all their game accounts.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.alliance, r.rank, p.is_diplomat, p.has_been_in_alliance 
            FROM players p
            LEFT JOIN roster r ON p.ign = r.ign
            WHERE p.discord_id = %s
        ''', (discord_id,))
        rows = cursor.fetchall()

        result = {
            "alliances": set(),
            "ranks": set(),
            "is_diplomat": False,
            "has_accounts": len(rows) > 0,
            "had_alliance": False,
        }
        for alliance, rank, is_diplomat, has_been_in_alliance in rows:
            if alliance:
                result["alliances"].add(alliance)
            if rank:
                result["ranks"].add(rank)
            if is_diplomat:
                result["is_diplomat"] = True
            if has_been_in_alliance:
                result["had_alliance"] = True
                
        return result
    except Exception as e:
        logger.error(f"Error fetching user role data: {e}")
        return {"alliances": set(), "ranks": set(), "is_diplomat": False, "has_accounts": False, "had_alliance": False}
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_all_linked_discord_ids() -> list[int]:
    """Return all Discord IDs that have at least one linked game account."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT discord_id FROM players')
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching linked discord IDs: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_account_by_game_id(game_id: str) -> tuple | None:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.game_id, p.ign, p.discord_id, r.alliance, r.rank, p.is_diplomat 
            FROM players p
            LEFT JOIN roster r ON p.ign = r.ign
            WHERE p.game_id = %s
        ''', (game_id,))
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error fetching account: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def set_diplomat(game_id: str, is_diplomat: bool) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET is_diplomat = %s WHERE game_id = %s', (is_diplomat, game_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error setting diplomat status: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# ---------------------------------------------------------------------------
# Roster Management
# ---------------------------------------------------------------------------

def bulk_update_roster(entries: list[dict[str, str]], alliance: str, timestamp) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()

        for entry in entries:
            ign = entry["ign"]
            rank = entry.get("rank")

            cursor.execute('''
                INSERT INTO roster (ign, alliance, rank, last_updated)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ign)
                DO UPDATE SET
                    alliance = EXCLUDED.alliance,
                    rank = EXCLUDED.rank,
                    last_updated = EXCLUDED.last_updated
            ''', (ign, alliance, rank, timestamp))
            
            # Since they are matched with an active alliance, set has_been_in_alliance = 1
            cursor.execute('''
                UPDATE players SET has_been_in_alliance = TRUE WHERE ign = %s
            ''', (ign,))

        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error in bulk roster update: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def mark_absent(alliance: str, timestamp) -> int:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Delete old entries entirely, our players table tracks historical presence now
        cursor.execute('''
            DELETE FROM roster
            WHERE alliance = %s AND last_updated < %s
        ''', (alliance, timestamp))
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count
    except Exception as e:
        logger.error(f"Error marking absent accounts: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# ---------------------------------------------------------------------------
# Pings & Config
# ---------------------------------------------------------------------------

def get_ping_channel(category: str) -> str | None:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT channel_id FROM ping_channels WHERE category = %s', (category,))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Error fetching ping channel: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def set_ping_channel(category: str, channel_id: str) -> None:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ping_channels (category, channel_id)
            VALUES (%s, %s)
            ON CONFLICT (category)
            DO UPDATE SET channel_id = EXCLUDED.channel_id
        ''', (category, channel_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error setting ping channel: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_all_ping_roles() -> dict[str, list[str]]:
    """Returns a dictionary mapping category -> list of role names"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT category, role_name FROM ping_roles')
        roles = {}
        for category, role_name in cursor.fetchall():
            if category not in roles:
                roles[category] = []
            roles[category].append(role_name)
        return roles
    except Exception as e:
        logger.error(f"Error fetching ping roles: {e}")
        return {}
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def add_ping_role(role_name: str, category: str) -> None:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ping_roles (role_name, category)
            VALUES (%s, %s)
            ON CONFLICT (role_name) DO NOTHING
        ''', (role_name, category))
        conn.commit()
    except Exception as e:
        logger.error(f"Error adding ping role: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()
