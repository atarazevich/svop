# Decisions

## 2026-11-05 — Team model: teams.yaml, team folders, workflows, flat rules
A team is a row in `.claude/teams.yaml` plus `.claude/teams/<name>/role.md`; a process is `rules/<name>-workflow.md`, reused by teams through `workflows:`, and all rules live in one flat folder. Context: team and process were one thing, and a SVOP project loaded two copies of three workflows (#2).

## 2026-11-07 — Git without destructive cleanup
`worktrees.md` became `git.md`: no stash, outputs and baselines in the scratchpad, land with `--ff-only` so `git branch -d` works, stopped work on `abandoned/` branches. Context: the safety hook suggests `git stash` and then blocks `stash drop`, and squash-merged branches can only go with the blocked `branch -D`, so stashes and branches piled up across projects.

## 2026-11-07 — Communication runs daily on a schedule
Communication no longer waits for `stage done`: a launchd agent runs one headless pass a day (`schedule` in teams.yaml), picks at most three items since the last run, and asks the owner through the router (`bus`, since `claude -p` has no channel tools). Product owns a fourth CLAUDE.md section, Story. Context: content is born every day, not at stage ends, and session crons die with the session and expire after 7 days (#3).
