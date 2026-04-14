# Kingshot Role Manager - Micro Documentation

## Scope
This repository has two components:

1. `bot/`: Discord bot that verifies players, reconciles roster uploads, and syncs Discord roles.
2. `roster-script/`: Local OCR CLI that extracts roster JSON from video captures.

## Runtime Stack

### Bot
- Python 3.12+
- `discord.py`
- `aiohttp`
- `psycopg` (PostgreSQL)
- Container build via `Containerfile`
- Primary deployment target: k3s (Kubernetes)

### Roster Script
- Python 3.12+
- `pillow`, `pytesseract`, `thefuzz`
- Requires local FFmpeg + Tesseract

## Source Layout
- `bot/main.py`: bot entrypoint and cog loading
- `bot/cogs/verification.py`: `/verify`, `/sync`
- `bot/cogs/admin.py`: `/whois`, `/setplayer`, `/setdiplomat`, `/removediplomat`
- `bot/cogs/reconciliation.py`: `/upload_roster`
- `bot/cogs/events.py`: ping role commands
- `bot/services/database.py`: PostgreSQL schema initialization and DB helpers
- `bot/services/role_sync.py`: data-driven role assignment
- `bot/services/roster.py`: JSON validation, reconciliation orchestration
- `bot/db/schema.sql`: SQL bootstrap for PostgreSQL
- `k8s/`: Kubernetes manifests for deployment

## Environment Variables (Bot)
- `DISCORD_TOKEN`: Discord bot token
- `DATABASE_URL`: Postgres connection string (example: `postgresql://user:password@host:5432/kingshot_role_manager`)

## Data Model (PostgreSQL)

### `players`
- `game_id` TEXT PRIMARY KEY
- `discord_id` BIGINT NOT NULL
- `ign` TEXT NOT NULL
- `kingdom` INTEGER DEFAULT 0
- `level` INTEGER DEFAULT 0
- `is_diplomat` BOOLEAN DEFAULT FALSE
- `has_been_in_alliance` BOOLEAN DEFAULT FALSE

### `roster`
- `ign` TEXT PRIMARY KEY
- `alliance` TEXT NOT NULL
- `rank` TEXT NOT NULL
- `last_updated` TIMESTAMPTZ NOT NULL

### `ping_channels`
- `category` TEXT PRIMARY KEY
- `channel_id` TEXT NOT NULL

### `ping_roles`
- `role_name` TEXT PRIMARY KEY
- `category` TEXT NOT NULL

## Command Behavior Notes

### `/upload_roster`
- Requires officer permission (Admin, R4, or R5).
- Requires two inputs: JSON file + alliance selection (`BOO` or `ZEN`).
- JSON entries must contain `ign`; `rank` is optional but validated when present.
- `alliance` inside each JSON row is optional. If present, it must match the slash command alliance.
- Reconciliation flow:
  1. Validate payload
  2. Upsert roster rows for selected alliance
  3. Remove absent rows by timestamp diff
  4. Run role sync for linked Discord users

## Role Sync Summary
- Active roster player -> `Member` + alliance role + rank role
- Linked player never seen in roster -> `Guest`
- Previously seen in roster, now absent -> `Ex-Member`
- Diplomat flag adds `Diplomat`

## Deployment Summary
- Kubernetes (k3s) is the main deployment path.
- Use manifests in `k8s/` and provide `DISCORD_TOKEN` + `DATABASE_URL` through secret data.
- Local container runs can still use `bot/compose.yaml` for testing with a local Postgres container.
