# Kingshot Alliance Manager Bot - AI Agent Specification

## 1. Project Overview
This project is a custom Discord bot built to manage a mobile game alliance (BOO) and its academy (ZEN). It acts as a "Virtual DOM" for the alliance, mapping in-game accounts to Discord users via a SQLite database, and automatically syncing Discord roles using video-to-text OCR state reconciliation.

## 2. Tech Stack & Environment
* **Language:** Python 3.12+
* **Framework:** `discord.py`
* **Package Manager:** `uv` (Fast Python package installer and resolver)
* **Database:** SQLite3 (Local file-based database)
* **Deployment:** Podman (Use `python:3.12-slim` to ensure compatibility with C-extensions for video/image processing; avoid `alpine`).
* **External Tools:** FFmpeg (for video frame extraction), Tesseract-OCR or Google Cloud Vision API (for text extraction).

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

## 4. Database Schema (The Virtual DOM)
Use a flattened relational structure to map multiple game accounts to single Discord users in a flat list (treating all accounts with equal weight).

**Table 1: `discord_users`**
* `discord_id` (Primary Key, Integer)

**Table 2: `game_accounts`**
* `game_id` (Primary Key, String) - The Kingshot Player ID
* `ign` (String) - In-Game Name
* `discord_id` (Foreign Key -> discord_users.discord_id)
* `alliance` (String, nullable) - e.g., 'BOO', 'ZEN', or NULL
* `rank` (String, nullable) - e.g., 'R1', 'R2', 'R3', 'R4', 'R5'
* `last_updated` (Datetime) - Timestamp of the last OCR scan this account appeared in.

## 5. Implementation Phases (Feature Roadmap)

### Phase 1: Infrastructure & DB (`feature/#1-infrastructure`)
* Initialize the project using `uv init`.
* Set up `discord.py` with an intents-enabled bot (specifically Message Content and Members intents).
* Write the initialization logic for the SQLite database to create tables if they do not exist.
* Write the container file using `python:3.12-slim`, ensuring FFmpeg and any OCR system dependencies are installed via `apt-get`.
* Create the `compose.yaml` file mapping the SQLite volume to the host for persistence.

### Phase 2: Reaction Role Welcome Gate (`feature/#2-reaction-roles`)
* **Goal:** Handle the initial onboarding in the `#rules` channel natively, replacing third-party bots.
* **Logic:** 
  * Listen to raw reaction add/remove events (`on_raw_reaction_add`) on a specific message ID in the `#rules` channel.
  * 🟢 "Guest" emoji -> Assigns `Guest` role.
  * 🤝 "Diplomat" emoji -> Assigns `verify-diplomat` role.
  * ⚔️ "Member" emoji -> Assigns `verify-member` role.
  * Support auto-reacting the emojis on startup purely for user convenience.
* Ensure the bot gracefully handles removing the role if the user removes their reaction.

### Phase 3: The Verification Command (`feature/#3-verification-api`)
* **Goal:** Link game accounts to Discord IDs via web API check.
* **Logic:**
  * Listen for `!verify <PlayerID>` in the `#member-verification` channel.
  * Make an HTTP GET request to `https://kingshot.net/api/player-info?playerId={PlayerID}` to validate the Player ID and fetch the In-Game Name (IGN) from the JSON response.
  * Prompt the user in chat: *"Found account [IGN]. Is this your username? Type 'yes' to confirm."*
  * On confirmation, write/update the records in `discord_users` and `game_accounts` caching their IGN.
  * Implement `!sync` (or `!sync <@user>`) to force an API re-sync of a user's cached IGN in case they use a rename item in-game.

### Phase 4: Event Ping Roles (`feature/#4-event-pings`)
* **Goal:** Setup the reaction-role message specifically for event pings.
* **Logic:**
  * There are two channels created for this: `set-pings` (in ZEN) and `set-pings` (in BOO).
  * The bot will post/manage a message in these channels allowing users to react to opt-in to specific event pings (e.g. "Bearhunt", "Arena").
  * *Note: A separate bot will handle actually pinging these roles during the events.*

### Phase 5: Administration & Lookups (`feature/#5-admin-tools`)
* **Goal:** Allow manual registration and rapid data lookups.
* **Logic:**
  * `!whois <@DiscordUser>`: Queries the database and returns all IGNs tied to that Discord member. Anyone can run this command.
  * `!setplayer <@DiscordUser> <game_id>`: Restricted to members with the `"Verifier"` role. Queries the API for the IGN and manually forces the link into the database without user confirmation.

### Phase 6: Video Processing Pipeline (`feature/#6-ffmpeg-pipeline`)
* **Goal:** Ingest alliance roster screen recordings.
* **Logic:**
  * Listen for `.mp4` attachments uploaded by Admins/R4s in the `#roster-updates` channel.
  * Download the video to a `/tmp` directory.
  * Use a Python wrapper for FFmpeg to extract exactly 1 frame every second to prevent redundant processing.
  * Store extracted frames locally and prepare them for Phase 7.

### Phase 7: OCR Engine & Parsing (`feature/#7-ocr-engine`)
* **Goal:** Convert video frames into structured JSON data.
* **Logic:**
  * Pass the extracted frames through Tesseract-OCR.
  * Parse the text output using Regex to identify keywords: `R5`, `R4`, `R3`, `R2`, `R1` and the adjacent player names.
  * Handle edge cases and OCR hallucinations using Fuzzy String Matching (`FuzzyWuzzy` or `TheFuzz`).
  * Output a deduplicated list of dictionaries: `[{"ign": "DarkLord99", "rank": "R4", "alliance": "BOO"}]`.

### Phase 8: State Reconciliation & Auto-Kicks (`feature/#8-reconciliation`)
* **Goal:** The core engine. Diff the OCR data against the SQLite DB to assign roles and detect kicks.
* **Logic:**
  * 1. Capture the exact timestamp of the scan (e.g., `T_Now`).
  * 2. Iterate through the OCR JSON. For every `ign`, update their DB row: `alliance = 'BOO'` or `'ZEN'`, update `rank`, set `last_updated = T_Now`.
  * 3. **Absence Detection:** Query DB for updated accounts where `last_updated < T_Now`. Set these to `alliance = NULL` (they were kicked/left).
  * 4. **Role Sync:** Iterate through all Discord IDs in the DB.
    * If they have an active BOO account, ensure they have the BOO Discord role.
    * If they have an active ZEN account, ensure they have the ZEN role.
    * If all their accounts are `NULL` (kicked), strip alliance roles and assign the `Ex-Member` role.
  * 5. Post a summary report in `#roster-updates` detailing who was added, updated, and removed.