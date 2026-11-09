# Decisions

## 2026-11-05 — Team model: teams.yaml, team folders, workflows, flat rules
A team is a row in `.claude/teams.yaml` plus `.claude/teams/<name>/role.md`; a process is `rules/<name>-workflow.md`, reused by teams through `workflows:`, and all rules live in one flat folder. Context: team and process were one thing, and a SVOP project loaded two copies of three workflows (#2).

## 2026-11-07 — Git without destructive cleanup
`worktrees.md` became `git.md`: no stash, outputs and baselines in the scratchpad, land with `--ff-only` so `git branch -d` works, stopped work on `abandoned/` branches. Context: the safety hook suggests `git stash` and then blocks `stash drop`, and squash-merged branches can only go with the blocked `branch -D`, so stashes and branches piled up across projects.

## 2026-11-07 — Communication runs daily on a schedule
Communication no longer waits for `stage done`: a launchd agent runs one headless pass a day (`schedule` in teams.yaml), picks at most three items since the last run, and asks the owner through the router (`bus`, since `claude -p` has no channel tools). Product owns a fourth CLAUDE.md section, Story. Context: content is born every day, not at stage ends, and session crons die with the session and expire after 7 days (#3).

## 2026-11-08 — The plan is kept by the orchestrator with a `plan` skill
No separate product team for now: `rules/plan.md` holds three triggers (fold, next, review) and `skills/plan/` holds the steps and the Stages format with a required Done when. Context: owner input that was planning got treated as tasks, and decisions were not checked against earlier ones; the owner chose one place for the plan over a new role (2026-11-08).

## 2026-11-08 — A closed stage gets an owner page
`plan` next writes `docs/owner/stages/<n>-<slug>.html` before it marks a stage done, and keeps `docs/owner/index.html`, served on the tailnet at `/<project>/`. Context: stages may run without the owner; he catches up from one page, and communication uses it as material.

## 2026-11-08 — Stages in docs/plan.md; a CLAUDE.md contract
Stages moved from `CLAUDE.md` to `docs/plan.md`, read only by the `plan` skill. `CLAUDE.md` holds only About, Principles, Decisions in force, Story and a one-line current stage (`knowledge.md`). Context: `CLAUDE.md` loads into every session and subagent, so detailed stages were dead weight there.

## 2026-11-09 — CLAUDE.md has a Goal slot
`Goal` is the first section of the CLAUDE.md contract: the near goal, measurable and visible from outside. It is a slot: empty is fine. Nothing is gated on it; the plan skill mentions it only when clearly relevant; the owner index shows it first. Context: the owner wants every project tied to a goal, but the goal forms in the owner's own time ("процесс внутри человека происходит"), so it is never forced (04:35, softened 04:40).
