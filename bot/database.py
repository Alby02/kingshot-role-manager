import sqlite3
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "data/kingshot.db")

def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db() -> None:
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discord_users (
                discord_id INTEGER PRIMARY KEY
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_accounts (
                game_id TEXT PRIMARY KEY,
                ign TEXT NOT NULL,
                discord_id INTEGER,
                alliance TEXT,
                rank TEXT,
                is_diplomat INTEGER DEFAULT 0,
                last_updated DATETIME,
                FOREIGN KEY(discord_id) REFERENCES discord_users(discord_id)
            )
        ''')

        # Migration: add is_diplomat column if missing (for existing DBs)
        cursor.execute("PRAGMA table_info(game_accounts)")
        columns = [row[1] for row in cursor.fetchall()]
        if "is_diplomat" not in columns:
            cursor.execute("ALTER TABLE game_accounts ADD COLUMN is_diplomat INTEGER DEFAULT 0")
            logger.info("Migrated database: added is_diplomat column")

        conn.commit()
        logger.info(f"Database initialized successfully at {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# ---------------------------------------------------------------------------
# User & Account Registration
# ---------------------------------------------------------------------------

def register_user(discord_id: int, game_id: str, ign: str) -> None:
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('INSERT OR IGNORE INTO discord_users (discord_id) VALUES (?)', (discord_id,))
        
        cursor.execute('''
            INSERT OR REPLACE INTO game_accounts (game_id, ign, discord_id) 
            VALUES (?, ?, ?)
        ''', (game_id, ign, discord_id))

        conn.commit()
    except Exception as e:
        logger.error(f"Error registering user in DB: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def update_ign(discord_id: int, game_id: str, ign: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT discord_id FROM game_accounts WHERE game_id = ?', (game_id,))
        row = cursor.fetchone()
        if not row or row[0] != discord_id:
            return False

        cursor.execute('UPDATE game_accounts SET ign = ? WHERE game_id = ?', (ign, game_id))
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
    """Return all game accounts linked to a Discord user."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT game_id, ign, alliance, rank, is_diplomat FROM game_accounts WHERE discord_id = ?',
            (discord_id,),
        )
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

    Returns dict with keys:
        alliances: set of active alliance tags (e.g. {'BOO', 'ZEN'})
        ranks:     set of rank strings (e.g. {'R4'})
        is_diplomat: bool
        has_accounts: bool - whether the user has any linked accounts at all
        had_alliance: bool - whether ANY account ever had an alliance (last_updated not null)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT alliance, rank, is_diplomat, last_updated FROM game_accounts WHERE discord_id = ?',
            (discord_id,),
        )
        rows = cursor.fetchall()

        result = {
            "alliances": set(),
            "ranks": set(),
            "is_diplomat": False,
            "has_accounts": len(rows) > 0,
            "had_alliance": False,
        }
        for alliance, rank, is_diplomat, last_updated in rows:
            if alliance:
                result["alliances"].add(alliance)
            if rank:
                result["ranks"].add(rank)
            if is_diplomat:
                result["is_diplomat"] = True
            if last_updated:
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
        cursor.execute('SELECT DISTINCT discord_id FROM game_accounts WHERE discord_id IS NOT NULL')
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching linked discord IDs: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# ---------------------------------------------------------------------------
# Diplomat management
# ---------------------------------------------------------------------------

def set_diplomat(game_id: str, is_diplomat: bool) -> bool:
    """Toggle diplomat status for a game account. Returns True if the account exists."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE game_accounts SET is_diplomat = ? WHERE game_id = ?',
            (1 if is_diplomat else 0, game_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error setting diplomat status: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_account_by_game_id(game_id: str) -> tuple | None:
    """Return a single game account row or None."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT game_id, ign, discord_id, alliance, rank, is_diplomat FROM game_accounts WHERE game_id = ?',
            (game_id,),
        )
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error fetching account: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# ---------------------------------------------------------------------------
# Reconciliation (bulk roster updates)
# ---------------------------------------------------------------------------

def bulk_update_roster(entries: list[dict[str, str]], alliance: str, timestamp: str) -> bool:
    """
    Batch upsert from a roster JSON.

    Each entry: {"ign": "...", "rank": "R1"-"R5"}
    The alliance tag is applied to all entries.

    For accounts that already exist and are linked to a Discord user,
    only alliance, rank, and last_updated are touched (ign updated from roster).
    For accounts NOT yet in the DB, they are created WITHOUT a discord_id
    (they become "known but unlinked" accounts).
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        for entry in entries:
            ign = entry["ign"]
            rank = entry.get("rank")

            # Check if this IGN already exists (match by ign since roster has no game_id)
            cursor.execute('SELECT game_id, discord_id FROM game_accounts WHERE ign = ?', (ign,))
            row = cursor.fetchone()

            if row:
                # Update existing account
                cursor.execute('''
                    UPDATE game_accounts 
                    SET alliance = ?, rank = ?, last_updated = ?, ign = ?
                    WHERE game_id = ?
                ''', (alliance, rank, timestamp, ign, row[0]))
            else:
                # Insert as unlinked account (game_id = ign as placeholder until verified)
                cursor.execute('''
                    INSERT OR IGNORE INTO game_accounts (game_id, ign, alliance, rank, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                ''', (ign, ign, alliance, rank, timestamp))

        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error in bulk roster update: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def mark_absent(alliance: str, timestamp: str) -> int:
    """
    For the given alliance, set alliance = NULL for any account whose
    last_updated is older than the scan timestamp. Returns count of affected rows.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE game_accounts
            SET alliance = NULL, rank = NULL
            WHERE alliance = ? AND (last_updated IS NULL OR last_updated < ?)
        ''', (alliance, timestamp))
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        logger.error(f"Error marking absent accounts: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_accounts_by_alliance(alliance: str) -> list[tuple]:
    """Return all game accounts currently in the given alliance."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT game_id, ign, discord_id, rank, is_diplomat FROM game_accounts WHERE alliance = ?',
            (alliance,),
        )
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error fetching alliance accounts: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
