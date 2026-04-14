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
