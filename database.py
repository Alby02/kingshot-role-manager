import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "data/kingshot.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
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
                last_updated DATETIME,
                FOREIGN KEY(discord_id) REFERENCES discord_users(discord_id)
            )
        ''')

        conn.commit()
        logger.info(f"Database initialized successfully at {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def register_user(discord_id: int, game_id: str, ign: str):
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
