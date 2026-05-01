# Kingshot Role Manager

Discord automation for alliance operations in Kingshot.

This project links Discord users to Kingshot accounts, reconciles alliance rosters from JSON uploads, and automatically assigns/removes roles based on roster state.

## Repository Structure

- `bot/`: Discord bot service
- `roster-script/`: local OCR extraction CLI
- `instruction.md`: concise project micro-docs

## Features

- `/verify <player_id>` to link a Kingshot account
- `/sync <player_id>` to refresh account data from API
- `/upload_roster <file> <alliance>` to reconcile alliance state
- `/roster_diff <file> <alliance>` to preview roster changes
- `/reconcile_alliance <alliance> [dry_run]` to force role reconciliation
- Automatic role sync (`Guest`, `Member`, `Ex-Member`, `Diplomat`, alliance roles, rank roles)
- Admin/manager commands (`/whois`, `/setplayer`, `/removeplayer`, `/setdiplomat`, `/removediplomat`)
- Event ping role management (`/pings`, `/create_ping`, `/set_ping_channel`, `/schedule_ping`, `/ping_config`)

### Permission roles

The bot auto-creates missing managed roles when possible.

- `roster-manager` (or admin): can run `/upload_roster`, `/roster_diff`, `/reconcile_alliance`, `/setplayer`, or `/removeplayer`
- `R4`/`R5` (or admin): can run `/setdiplomat`, `/removediplomat`, and `/schedule_ping`

## Roster Script

See `roster-script/README.md` for OCR extraction workflow.

Setup for the OCR tools is documented there as well, including installs for FFmpeg and Tesseract.

JSON entries only need `ign` and optionally `rank`.

## Deployment

The bot and database are designed to be deployed to a Kubernetes (k3s) cluster using custom Helm charts and `helmfile`. See the infrastructure repository (if applicable) for deployment configurations.

## Contributing

See `CONTRIBUTING.md` for development workflow, coding rules, and pull request expectations.

## License

Licensed under the terms in `LICENSE`.
