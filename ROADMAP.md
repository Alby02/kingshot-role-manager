# Roadmap

## In Progress
- Docs

## Planned
- [x] Finish role policy updates
  - [x] Add `roster-manager` role gate for `/upload_roster`
  - [x] Add `roster-manager` gate for `/setplayer`
  - [x] Split diplomat commands into dedicated cog
- [x] Roster operations
  - [x] Add `/roster_diff` preview command
  - [x] Add `/reconcile_alliance` with dry-run mode
- [x] Sync/Reconciliation strategy
  - [x] Preserve roster linkage on IGN rename during `/sync` when safe
- [x] Ping system
  - [x] Auto-create ping roles
  - [x] Ping role selector command
  - [x] Command Add/Remove ping (recurring settings)
- [ ] Daily task reminder system
  - [ ] Define schedule
  - [ ] Define reminder audiences and role targeting
  - [ ] Implement scheduler job and delivery rules
- [ ] Docs, Deployment, GitOps, Testing and quality
  - [ ] Make a proper README.md
  - [ ] Make a proper ROADMAP.md
  - [ ] Make a proper CONTRIBUTING.md
  - [ ] Make a proper INSTRUCTIONS.md
  - [ ] Make a proper CHANGELOG.txt
  - [x] Add Helm chart
  - [x] Add image tag automation
  - [ ] Add unit tests
  - [ ] Add integration test
  - [x] Add CI lint/type-check steps

## Maybe Later
- [ ] Optional split of roster script into independent repository
- [ ] Ping setup webpage
- [ ] Reminders setup webpage

## Not Planned
- [ ] Add support for other alliances (generic implementation)
- [ ] Add support for multiple kingdoms
