# Contributing Guide

Thanks for contributing to Kingshot Role Manager.

## Development Workflow

1. Create a branch from `dev`.
2. Make focused changes with clear commits.
3. Test locally before opening a PR.
4. Open PR into `dev` unless it is an emergency hotfix.

Recommended branch naming:

- `feature/<short-name>`
- `bugfix/<short-name>`
- `hotfix/<short-name>`

## Local Setup

### Bot

```bash
cd bot
uv sync
```

Set env vars:

- `DISCORD_TOKEN`
- `DATABASE_URL`

Initialize DB:

```bash
psql "$DATABASE_URL" -f db/schema.sql
```

Run:

```bash
uv run python main.py
```

### Roster Script

```bash
cd roster-script
uv sync
```

Install system tools:

- FFmpeg
- Tesseract OCR

## Coding Standards

- Keep code changes small and intentional.
- Preserve existing command behavior unless change is explicit.
- Add logging for operationally relevant events and failures.
- Prefer clear function names and typed signatures.
- Avoid adding dependencies unless there is a strong reason.

## Database Changes

When modifying schema:

1. Update `bot/db/schema.sql`.
2. Update `bot/services/database.py` init schema if needed.
3. Document migration/backfill steps in PR description.

## Pull Request Checklist

- [ ] Behavior change is documented.
- [ ] Commands still register and execute.
- [ ] DB queries tested against PostgreSQL.
- [ ] Roster upload path validated with sample JSON.
- [ ] README and micro-docs updated if needed.

## Testing Suggestions

- Verify `/verify` and `/sync` for linked account behavior.
- Verify `/upload_roster` with alliance selected and valid JSON.
- Verify role transitions: `Guest` -> `Member`, `Member` -> `Ex-Member`.
- Verify diplomat toggles still apply/remove `Diplomat` role.

## Security and Secrets

- Never commit tokens or database credentials.
- Keep real secret manifests out of git.
- Use environment variables or Kubernetes secrets only.
