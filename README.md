# Kingshot Role Manager

Discord automation for alliance operations in Kingshot.

This project links Discord users to Kingshot accounts, reconciles alliance rosters from JSON uploads, and automatically assigns/removes roles based on roster state.

## Repository Structure

- `bot/`: Discord bot service
- `roster-script/`: local OCR extraction CLI
- `instruction.md`: concise probably wrong project micro-docs

## Features

- `/verify <player_id>` to link a Kingshot account
- `/sync <player_id>` to refresh account data from API
- `/upload_roster <file> <alliance>` to reconcile alliance state
- Automatic role sync (`Guest`, `Member`, `Ex-Member`, `Diplomat`, alliance roles, rank roles)
- Admin/manager commands (`/whois`, `/setplayer`, `/setdiplomat`, `/removediplomat`)
- Event ping role management (`/pings`, `/create_ping`, `/set_ping_channel`)

### Permission roles

The bot auto-creates missing managed roles when possible.

- `roster-manager` (or admin): can run `/upload_roster` or `/setplayer`
- `R4`/`R5` (or admin): can run `/setdiplomat` and `/removediplomat`

## Roster Script

See `roster-script/README.md` for OCR extraction workflow.

Setup for the OCR tools is documented there as well, including installs for FFmpeg and Tesseract.

JSON entries only need `ign` and optionally `rank`.

## Contributing

See `CONTRIBUTING.md` for development workflow, coding rules, and pull request expectations.

## License

Licensed under the terms in `LICENSE`.
