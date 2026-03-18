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
                discord_id INTEGER PRIMARY KEY,
                discord_name TEXT NOT NULL
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
