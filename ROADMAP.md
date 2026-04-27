# Roadmap

## In Progress
- Docs
- Helm Charts

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
- [ ] Ping system
  - [x] Auto-create ping roles
  - [x] Ping role selector command
  - [ ] Command Add/Remove ping (recurring settings)
  - [ ] Ping setup webpage
- [ ] Daily task reminder system
  - [ ] Define schedule
  - [ ] Define reminder audiences and role targeting
  - [ ] Implement scheduler job and delivery rules
- [ ] Docs, Deployment, GitOps, Testing and quality
  - [ ] Add Proper docs and Readme
  - [ ] Add Helm chart
  - [ ] Add image tag automation integration notes
  - [ ] Add unit tests
  - [ ] Add integration test
  - [ ] Add CI lint/type-check steps

## Later
- [ ] Optional split of roster script into independent repository
