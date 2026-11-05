# Decisions

## 2026-11-05 — Team model: teams.yaml, team folders, workflows, flat rules
A team is a row in `.claude/teams.yaml` plus `.claude/teams/<name>/role.md`; a process is `rules/<name>-workflow.md`, reused by teams through `workflows:`, and all rules live in one flat folder. Context: team and process were one thing, and a SVOP project loaded two copies of three workflows (#2).
