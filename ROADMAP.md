# Roadmap

## In Progress
- [ ] Bot source layout migration to src package (`bot/src/kingshot_role_manager`)
- [ ] Command/cog cleanup and permission hardening
- [ ] Sync and reconciliation strategy finalization

## Planned
- [ ] Finish role policy updates
  - [x] Add `roster-manager` role gate for `/upload_roster`
  - [x] Add `player-manager`/`roster-manager` gate for `/setplayer`
  - [x] Split diplomat commands into dedicated cog
  - [ ] Add command-level audit logging for privileged actions
- [ ] Roster operations
  - [x] Add `/roster_diff` preview command
  - [x] Add `/reconcile_alliance` with dry-run mode
  - [ ] Add richer diff output pagination for large alliances
- [ ] Sync/Reconciliation strategy
  - [x] Preserve roster linkage on IGN rename during `/sync` when safe
  - [ ] Add optional strict mode (no implicit roster rename carry-over)
  - [ ] Add metrics around rename carry-over events
- [ ] Ping system improvements
  - [x] Auto-create missing ping roles
  - [ ] Add list/remove ping role commands
  - [ ] Add category validation/autocomplete
- [ ] Daily task reminder system (TBD)
  - [ ] Define schedule source (DB vs config)
  - [ ] Define reminder audiences and role targeting
  - [ ] Implement scheduler job and delivery rules
- [ ] Deployment and GitOps
  - [x] Add Helm chart scaffold
  - [ ] Add Argo CD values examples per environment
  - [ ] Add image tag automation integration notes
- [ ] Testing and quality
  - [ ] Add unit tests for permission helpers
  - [ ] Add integration test for role-sync role creation
  - [ ] Add CI lint/type-check steps

## Later
- [ ] Optional split of roster script into independent repository
- [ ] Operator docs and runbook for incident handling
