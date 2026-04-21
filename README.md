# Kingshot Role Manager

Discord automation for alliance operations in Kingshot.

This project links Discord users to Kingshot accounts, reconciles alliance rosters from JSON uploads, and automatically assigns/removes roles based on roster state.

## Repository Structure

- `bot/`: Discord bot service
- `roster-script/`: local OCR extraction CLI
- `k8s/`: Kubernetes (k3s-friendly) deployment manifests
- `instruction.md`: concise project micro-docs

## Features

- `/verify <player_id>` to link a Kingshot account
- `/sync <player_id>` to refresh account data from API
- `/upload_roster <file> <alliance>` to reconcile alliance state
- Automatic role sync (`Guest`, `Member`, `Ex-Member`, `Diplomat`, alliance roles, rank roles)
- Admin/manager commands (`/whois`, `/setplayer`, `/setdiplomat`, `/removediplomat`)
- Event ping role management (`/pings`, `/create_ping`, `/set_ping_channel`)

## Tech Stack

- Python 3.12+
- `discord.py`
- PostgreSQL (`psycopg`)
- `aiohttp`
- Optional local OCR utility with FFmpeg + Tesseract


## Quick Start (Bot)

### 1. Install dependencies

```bash
cd bot
uv sync
```

### 2. Create PostgreSQL database

Create a database (example name: `kingshot_role_manager`) in your PostgreSQL instance, then run:

```bash
PGPASSWORD="$DATABASE_PASSWORD" psql -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -d "$DATABASE_NAME" -f db/schema.sql
```

### 3. Configure environment

Set these environment variables:

- `DISCORD_TOKEN`
- `DATABASE_HOST`
- `DATABASE_PORT` (optional, defaults to `5432`)
- `DATABASE_NAME`
- `DATABASE_USER`
- `DATABASE_PASSWORD`

### 4. Run bot locally

```bash
cd bot
uv run python -m kingshot_role_manager
```

### 5. Permission roles

The bot auto-creates missing managed roles when possible.

- `roster-manager`: can run `/upload_roster`
- `player-manager` or `roster-manager`: can run `/setplayer`
- `R4`/`R5` (or admin): can run `/setdiplomat` and `/removediplomat`

## Kubernetes Deployment (k3s)

### 1. Build and push bot image

Use your preferred registry and update image in `k8s/deployment.yaml`.

### 2. Create secret manifest

Copy `k8s/secret.example.yaml` to a private file, fill values, then apply it.

### 3. Deploy manifests

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f your-secret.yaml
kubectl apply -f k8s/deployment.yaml
```

Or with kustomize:

```bash
kubectl apply -k k8s/
```

## Local Container Run (Optional)

For local integration testing with a bundled PostgreSQL container:

```bash
cd bot
podman compose up -d --build
```

## Roster Script

See `roster-script/README.md` for OCR extraction workflow.

Setup for the OCR tools is documented there as well, including installs for FFmpeg and Tesseract.

JSON entries only need `ign` and optionally `rank`.

## Contributing

See `CONTRIBUTING.md` for development workflow, coding rules, and pull request expectations.

## License

Licensed under the terms in `LICENSE`.
