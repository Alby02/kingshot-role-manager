# Kingshot Alliance Manager — AI Agent Specification

## 1. Project Overview

This project manages a mobile game alliance (BOO) and its academy (ZEN) through two independent components:

1. **Bot** (`bot/`) — A Discord bot deployed on a VPS via Podman. It manages roles, links Discord users to Kingshot accounts, and automatically reconciles alliance rosters uploaded as JSON files.
2. **Roster Script** (`roster-script/`) — A local CLI tool that processes screen recordings of the Kingshot alliance member list, extracting roster data into JSON via FFmpeg + Tesseract OCR.

The bot acts as a "Virtual DOM" for the alliance, mapping in-game accounts to Discord users via a SQLite database. Roles are assigned automatically based on database state — not via emoji reactions.

## 2. Tech Stack & Environment

### Bot (`bot/`)
* **Language:** Python 3.12+
* **Framework:** `discord.py`
* **Package Manager:** `uv`
* **Database:** SQLite3 (file-based, volume-mapped)
* **HTTP Client:** `aiohttp` (for Kingshot API calls)
* **Deployment:** Podman container (`python:3.12-slim`)

### Roster Script (`roster-script/`)
* **Language:** Python 3.12+
* **Package Manager:** `uv`
* **Dependencies:** `pillow`, `pytesseract`, `thefuzz`
* **System Requirements:** FFmpeg, Tesseract-OCR (installed locally)
* **Runs:** Locally on the operator's machine

## 3. Git Workflow & Branching Strategy

The project strictly adheres to a three-branch Git flow. Do not commit directly to base branches.
* **Base Branches:**
  * `main`: Production-ready code.
  * `QA`: Stable testing environment.
  * `dev`: Active integration branch for new developments.
* **Ephemeral Branches:**
  * `feature/#x-featurename`: Cut from `dev` for new features.
  * `bugfix/#x-bugfix`: Cut from `QA` for bugfixes.
  * `hotfix/#x-fixname`: Cut from `main` for critical production hotfixes.

## 4. Project Structure

```
kingshot-role-manager/
├── bot/                              # Discord bot (runs on VPS)
│   ├── main.py                       # Bot entry point
│   ├── database.py                   # SQLite schema, queries, migrations
│   ├── role_sync.py                  # Data-driven Discord role assignment
│   ├── cogs/
│   │   ├── verification.py           # !verify, !sync commands
│   │   ├── events.py                 # Event ping reaction roles
│   │   ├── admin.py                  # !whois, !setplayer, !setdiplomat, !removediplomat
│   │   └── reconciliation.py         # JSON upload watcher + roster reconciliation
│   ├── Containerfile
│   ├── compose.yaml
│   ├── pyproject.toml
│   └── data/
│       └── pings.json                # Event ping role configuration
│
├── roster-script/                    # OCR extraction tool (runs locally)
│   ├── roster_script/
│   │   ├── __main__.py               # CLI entry point
│   │   ├── extractor.py              # FFmpeg frame extraction
│   │   └── ocr.py                    # Tesseract OCR + regex parsing + fuzzy dedup
│   ├── pyproject.toml
│   └── README.md
│
├── instruction.md
├── .gitignore
└── LICENSE
```

## 5. Database Schema

Flattened relational structure mapping multiple game accounts to single Discord users.

**Table 1: `discord_users`**
* `discord_id` (Primary Key, Integer)

**Table 2: `game_accounts`**
* `game_id` (Primary Key, String) — The Kingshot Player ID
* `ign` (String) — In-Game Name
* `discord_id` (Foreign Key -> discord_users.discord_id, nullable)
* `alliance` (String, nullable) — `'BOO'`, `'ZEN'`, or `NULL`
* `rank` (String, nullable) — `'R1'`, `'R2'`, `'R3'`, `'R4'`, `'R5'`
* `is_diplomat` (Integer, default 0) — `1` if the account is marked as Diplomat
* `last_updated` (Datetime) — Timestamp of the last roster scan this account appeared in

## 6. Role Assignment Model

Roles are **not** assigned via emoji reactions. They are computed from database state and applied automatically after verification, roster reconciliation, or admin commands.

| Condition | Discord Roles Assigned |
|---|---|
| Verified via `!verify`, no alliance data | `Guest` |
| Active in BOO roster | `Member`, `BOO`, rank role (R1–R5) |
| Active in ZEN roster | `Member`, `ZEN`, rank role (R1–R5) |
| Marked as diplomat by R4/R5 | `Diplomat` (additive, stacks with above) |
| Was in roster but no longer appears | Strip alliance/rank roles, assign `Ex-Member` |

**Role sync is triggered by:**
* `!verify` — after linking an account
* `!sync` — after refreshing an IGN
* `!setplayer` — after admin-linking an account
* `!setdiplomat` / `!removediplomat` — after toggling diplomat status
* JSON upload to `#roster-updates` — bulk sync for all linked users

## 7. Environment Variables

Stored in `bot/.env` (git-ignored):

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Bot authentication token |
| `RULES_CHANNEL_ID` | Channel ID for the rules channel |
| `RULES_MESSAGE_ID` | Message ID for the rules message |
| `PING_CHANNEL_BOO_ID` | Channel ID for BOO event ping opt-in |
| `PING_CHANNEL_ZEN_ID` | Channel ID for ZEN event ping opt-in |
| `ROSTER_CHANNEL_ID` | Channel ID for `#roster-updates` (JSON uploads) |
| `DB_PATH` | SQLite database path (default: `data/kingshot.db`) |

## 8. Implementation Phases (Feature Roadmap)

### Phase 1: Infrastructure & DB (`feature/#1-infrastructure`) ✅
* Initialize the project using `uv init`.
* Set up `discord.py` with an intents-enabled bot (Message Content and Members intents).
* Write the initialization logic for the SQLite database.
* Write the Containerfile using `python:3.12-slim`.
* Create the `compose.yaml` file mapping the SQLite volume to the host.

### Phase 2: Data-Driven Role Assignment (`feature/#6-project-restructure`) ✅
* **Replaces the old reaction-role system.**
* Roles (`Guest`, `Member`, `Diplomat`, `Ex-Member`, alliance tags, ranks) are computed from database state via `role_sync.py`.
* Role sync is called automatically after verification, reconciliation, and admin commands.
* No reaction-based role assignment for Guest/Diplomat/Member.

### Phase 3: The Verification Command (`feature/#3-verification-api`) ✅
* **Goal:** Link game accounts to Discord IDs via web API check.
* `!verify <PlayerID>` — Validates via `https://kingshot.net/api/player-info`, prompts with interactive buttons, links account in DB, auto-syncs roles.
* `!sync <PlayerID>` — Force re-sync of a cached IGN from the API.
* Available to all server members.

### Phase 4: Event Ping Roles (`feature/#4-event-pings`) ✅
* Event ping opt-in via reaction roles in `set-pings` channels (BOO and ZEN).
* Bot posts/manages reaction menus, and assigns ping roles like `Bear1-BOO`, `Arena`, etc.
* Configuration stored in `data/pings.json`.

### Phase 5: Administration & Lookups (`feature/#5-admin-tools`) ✅
* `!whois <@User>` — Lookup all linked Kingshot accounts for a Discord user. Displays IGN, alliance, rank, diplomat status.
* `!setplayer <@User> <GameID>` — Restricted to `Verifier` role. Admin-links accounts without user confirmation.
* `!setdiplomat <GameID>` — R4/R5/Admin only. Marks a game account as Diplomat, auto-syncs roles.
* `!removediplomat <GameID>` — R4/R5/Admin only. Removes diplomat status.

### Phase 6: Roster Script (`roster-script/`) ✅
* **Goal:** Local CLI tool to extract alliance roster from screen recordings.
* **Runs locally**, not on the VPS. Separate `pyproject.toml`.
* Uses FFmpeg to extract frames (1 fps default, configurable).
* Uses Tesseract OCR to read rank headers and player names.
* Uses fuzzy string matching (`thefuzz`) to deduplicate across frames.
* Outputs JSON: `[{"ign": "DarkLord99", "rank": "R4", "alliance": "BOO"}]`
* Usage: `uv run roster video.mp4 --alliance BOO --output roster.json`

### Phase 7: State Reconciliation (`feature/#6-project-restructure`) ✅
* **Goal:** Diff roster JSON against the database to assign roles and detect kicks.
* Bot watches `#roster-updates` for `.json` file uploads (R4/R5/Admin only).
* **Logic:**
  1. Validate uploaded JSON structure.
  2. Bulk-upsert all roster entries (update alliance, rank, last_updated).
  3. Mark absent accounts: any account in that alliance whose `last_updated < scan_timestamp` gets `alliance = NULL`.
  4. Bulk sync Discord roles for all linked users via `role_sync.sync_all_users()`.
  5. Post a summary embed in the channel (entries processed, removed, role sync stats).

### Phase 8: Event System Overhaul (`feature/#8-event-system`) 🔜
* **Goal:** Full event scheduling and ping management system.
* **Planned features:**
  * Bot sends scheduled pings (recurring or one-time, times in UTC+0).
  * Web dashboard to add/remove events, manage schedules, create/delete ping roles.
  * User opt-in via reactions in BOO/ZEN set-pings channels.
  * New "Ping Updates" role: notifies users when ping roles are added/changed.
  * Pings can be enabled/disabled independently of role existence.
  * Dedicated ping channel for outgoing pings.

## 9. Deployment

### Bot (VPS)
```bash
cd bot/
podman compose up -d --build
```

### Roster Script (local)
```bash
cd roster-script/
uv sync
uv run roster video.mp4 --alliance BOO
# Then upload the output .json to #roster-updates on Discord
```