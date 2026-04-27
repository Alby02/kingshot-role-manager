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

## Database Changes

When modifying schema:

1. Update `bot/src/kingshot_role_manager/services/database.py` init schema if needed.
2. Document migration/backfill steps in PR description.

## Pull Request Checklist

- [ ] Behavior change is documented.
- [ ] Commands still register and execute.
- [ ] DB queries tested against PostgreSQL.
- [ ] Roster upload path validated with sample JSON.
- [ ] README and micro-docs updated if needed.

## Security and Secrets

- Never commit tokens