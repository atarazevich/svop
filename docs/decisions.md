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

## 2026-11-11 — teams.yaml says how each session starts; `svop` starts it
`teams.yaml` version 2 adds `root`, `repos`, `env_file`, `herdr` labels, `session_id` and `claude:` (Claude Code's own flags, passed through, session over project key by key). One script, `svop.py` (`up`, `start`, `stop`), replaces the hand recipe in `team.md` step 6. `session_id` is the only resume switch: a missing transcript is an error, never a fresh start. Context: the start recipe was prose in `team.md` and hardcoded flags in the Router's `orc.py`; the owner chose one file and one script, nothing else (#4).

## 2026-11-11 — svop answers the trust dialog in the pane
On a first start in a folder Claude Code has never opened, `svop start`/`up` reads the session's pane and, when the trust dialog is fully drawn and the folder is inside the project root, moves to "Yes, I trust this folder" and presses Enter; it stops waiting when herdr reports the session's id. Context: Claude Code 2.1.322 has no CLI flag or setting to trust a folder for an interactive session (`--trust-workspace` is only for ultrareview; `-p` skips the dialog but is not interactive), and the other way, writing `hasTrustDialogAccepted` into `~/.claude.json`, edits Claude Code's own global state file. The dialog's default is "No, exit", so a blind Enter would quit; keys are sent only after the marker is read off the screen (#5).

## 2026-11-11 — Model defaults in the templates
The orchestrator starts on `model: fable`; each team on `model: opus` with `effort: medium`, so `svop up` gives it by default. Context: the owner's own running setup, set before the projects move to a server. A cheaper model for the developer subagent was considered and dropped for now.

## 2026-11-11 — Audience, promise, and the OpenClaw contrast
We write for solo builders who run several real products or clients and hit the wall of supervision. The promise: "the deeper your agents go, the clearer they come back"; the readable return leads, autonomy follows. The contrast with OpenClaw stays in the subtext. Context: audience research of 2026-11-11 (people who hit the wall go back to fewer sessions and ask for a return that reads in seconds); the owner confirmed.
