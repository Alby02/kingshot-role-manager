# Kingshot Role Manager - Micro Documentation

## Scope
This repository has two components:

1. `bot/`: Discord bot that verifies players, reconciles roster uploads, manages event pings, and syncs Discord roles.
2. `roster-script/`: Local OCR CLI that extracts roster JSON from video captures.

## Runtime Stack

### Bot
- Python 3.12+
- `discord.py`
- `curl_cffi` (for TLS spoofing Kingshot API)
- `psycopg` (PostgreSQL 18+)
- Container build via `Containerfile`
- Primary deployment target: k3s (Kubernetes) via custom Helm charts and `helmfile`

### Roster Script
- Python 3.12+
- `pillow`, `pytesseract`, `thefuzz`
- Requires local FFmpeg + Tesseract

## Source Layout
- `bot/src/kingshot_role_manager/__main__.py`: bot entrypoint and cog loading
- `bot/src/kingshot_role_manager/cogs/identity.py`: `/verify`, `/sync`, `/whois`, `/setplayer`, `/removeplayer`
- `bot/src/kingshot_role_manager/cogs/diplomacy.py`: `/setdiplomat`, `/removediplomat`
- `bot/src/kingshot_role_manager/cogs/roster.py`: `/upload_roster`, `/roster_diff`, `/reconcile_alliance`
- `bot/src/kingshot_role_manager/cogs/events.py`: `/pings`, `/create_ping`, `/set_ping_channel`, `/schedule_ping`, `/ping_config`
- `bot/src/kingshot_role_manager/ui/`: reusable Discord view components (`views.py`, `ping_views.py`)
- `bot/src/kingshot_role_manager/services/database.py`: PostgreSQL schema initialization and DB helpers
- `bot/src/kingshot_role_manager/services/role_sync.py`: data-driven role assignment
- `bot/src/kingshot_role_manager/services/roster.py`: JSON validation, reconciliation orchestration
- `bot/src/kingshot_role_manager/services/kingshot_api.py`: Kingshot Web API communication
- `bot/src/kingshot_role_manager/services/scheduler.py`: In-memory timer service for scheduled pings

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

### `ping_config`
- `category` TEXT PRIMARY KEY
- `channel_id` TEXT NOT NULL
- `roles` JSONB DEFAULT '[]'::jsonb

### `ping_schedules`
- `id` SERIAL PRIMARY KEY
- `role_name` TEXT NOT NULL
- `message` TEXT NOT NULL
- `send_at` TIMESTAMPTZ NOT NULL
- `recurrence` TEXT

## Command Behavior Notes

### Permission Role Gates
- `/upload_roster`, `/roster_diff`, `/reconcile_alliance`, `/setplayer`, and `/removeplayer`: requires `roster-manager` or Administrator
- `/setdiplomat`, `/removediplomat`, and `/schedule_ping`: requires `R4`, `R5`, or Administrator
- Missing managed roles are auto-created by the bot when permissions allow.

### `/upload_roster`, `/roster_diff`, `/reconcile_alliance`
- Requires roster permission (`roster-manager` or Admin).
- `/upload_roster` and `/roster_diff` require a JSON file + alliance selection (`BOO` or `ZEN`).
- JSON entries must contain `ign`; `rank`
- Reconciliation flow:
  1. Validate payload
  2. Upsert roster rows for selected alliance
  3. Remove absent rows by timestamp diff
- `/reconcile_alliance` allows forcing a sync based on the existing database state.

## Role Sync Summary
- Active roster player -> `Member` + alliance role + rank role
- Linked player never seen in roster -> `Guest`
- Previously seen in roster, now absent -> `Ex-Member`
- Diplomat flag adds `Diplomat`