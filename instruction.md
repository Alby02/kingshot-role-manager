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
- `bot/src/kingshot_role_manager/__main__.py`: bot entrypoint and cog loading
- `bot/src/kingshot_role_manager/cogs/verification.py`: `/verify`, `/sync`, `/setplayer`
- `bot/src/kingshot_role_manager/cogs/admin.py`: `/whois`
- `bot/src/kingshot_role_manager/cogs/diplomacy.py`: `/setdiplomat`, `/removediplomat`
- `bot/src/kingshot_role_manager/cogs/reconciliation.py`: `/upload_roster`
- `bot/src/kingshot_role_manager/cogs/events.py`: ping role commands
- `bot/src/kingshot_role_manager/ui/`: reusable Discord view components
- `bot/src/kingshot_role_manager/services/database.py`: PostgreSQL schema initialization and DB helpers
- `bot/src/kingshot_role_manager/services/role_sync.py`: data-driven role assignment
- `bot/src/kingshot_role_manager/services/roster.py`: JSON validation, reconciliation orchestration
- `bot/db/schema.sql`: SQL bootstrap for PostgreSQL
- `k8s/`: Kubernetes manifests for deployment

## Environment Variables (Bot)
- `DISCORD_TOKEN`: Discord bot token
- `DATABASE_HOST`: Postgres hostname
- `DATABASE_PORT`: Postgres port (defaults to `5432`)
- `DATABASE_NAME`: Postgres database name
- `DATABASE_USER`: Postgres username
- `DATABASE_PASSWORD`: Postgres password

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

### Permission Role Gates
- `/upload_roster`: requires `roster-manager` or Administrator
- `/setplayer`: requires `roster-manager`, `player-manager`, or Administrator
- `/setdiplomat` and `/removediplomat`: requires `R4`, `R5`, or Administrator
- Missing managed roles are auto-created by the bot when permissions allow.

### `/upload_roster`
- Requires roster permission (`roster-manager` or Admin).
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
- Use manifests in `k8s/` and provide `DISCORD_TOKEN` + database env vars through secret data.
- Local container runs can still use `bot/compose.yaml` for testing with a local Postgres container.
