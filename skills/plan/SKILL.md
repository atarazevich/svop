---
name: plan
description: Keep the project plan (docs/plan.md, plus Decisions, Story and the current-stage line in CLAUDE.md) current. Use for fold (owner input that is an idea, refinement or change of direction), next ("continue", "next", "погнали дальше"), and review (a piece of work closed with a result). Triggers come from rules/plan.md.
---

# Plan

The stages live in `docs/plan.md`; only this skill reads it. This skill also keeps the sections of `CLAUDE.md` (the contract in `knowledge.md`): About, Principles, Decisions in force, Story, and the one line with the current stage's name. Owner input on any of them is folded like any other. `docs/decisions.md` keeps each decision's context and the replaced ones. History is git of these three files. No other storage.

## Stages format

`docs/plan.md` starts with the owner pages address (below), then each stage, in order:

```
### <name> — <done | current | next | later>
- Slug: <slug>
- Goal: <one line: what this stage achieves>
- In it: <the problems or items, one line each, issue ids when they exist>
- Done when: <observable criteria>
```

- Exactly one stage is `current`. Order is the order in the file; stages have no numbers.
- **Slug**: short, lowercase, set once and never changed (e.g. `episode-0-level-2`). Refer to a stage by its slug everywhere: issues, pages, messages.
- `Done when` is required: without it, **next** cannot tell whether a stage is finished. A stage without it gets one before anything else. A `Done when` written by this skill and not yet confirmed by the owner ends with `(proposed)`; **next** asks the owner to confirm it before it closes the stage.
- Issues name their stage by slug (a GitHub milestone named by the slug, or `stage:` in an issue file). Closed issues are evidence; a stage is done only when its `Done when` holds.
- A plan without `- Slug:` lines: the first time this skill touches it, give each stage a slug and rename its existing page in `docs/owner/stages/` to `<slug>.html`.

## Open questions

- Blocking: nothing can move until the owner answers → ask him through the router (`confirm`).
- Not blocking → decide, go on, and tell him afterwards in one line, with the decision and why.

## fold

The owner gave an idea, a refinement or a change of direction.

1. Read `docs/plan.md`, the Decisions in `CLAUDE.md` and `docs/decisions.md`.
2. Put the input where it belongs: an item in the right stage, a new stage (usually `later`), a changed `Done when`, or a Decision. Keep the owner's words. A new stage without a `Done when` from the owner gets one you propose, marked `(proposed)`.
3. If it contradicts a Decision in force or an entry in `docs/decisions.md`, do not decide. Ask the owner through the router (`confirm`): the old decision, the new input, your recommendation. Change nothing until the answer.
4. Otherwise rebuild the index page (below), then commit what changed together (`docs/plan.md`, `CLAUDE.md`, `docs/owner/index.html`, a `docs/decisions.md` entry for a new decision), and tell the owner in one or two lines what changed, in the channel the input came from.

Fold plans; it never starts work.

## next

The owner said "continue", "next" or "погнали дальше".

1. Check the `current` stage against its `Done when`, with evidence (closed issues, results, commits).
2. Not met: tell the owner in one line what is missing, and continue that stage.
3. Met: write the stage page and update the index page (below). Then mark the stage `done` and make the first `next` stage `current` in `docs/plan.md`, and update the current-stage line in `CLAUDE.md`. Commit `docs/plan.md`, `CLAUDE.md` and the changed files in `docs/owner/` together, by name, on main (`git.md`). Check both links. No `next` stage left: ask the owner which `later` stage comes next.
4. Break the current stage into issues for development (`issues-workflow.md`), and send them to the teams (`team.md`).
5. Tell the owner in one line what closed, with the link to its page, and in one line what starts.

## Stage page

When a stage closes, it gets a page, so the owner can catch up on stages that ran without him: without using the product, without guessing from commits.

- **File**: `docs/owner/stages/<slug>.html`, one self-contained HTML file, readable on a phone, with the stage name, the date and the commit it was written from (`git rev-parse --short HEAD`) at the top.
- **Index**: `docs/owner/index.html`, built only by the script that ships with this skill: `python3 .claude/skills/plan/index.py` (from the project root). On top, from `CLAUDE.md`: About, Principles, Decisions, Story, Current stage. Below, from `docs/plan.md`: every stage with its status; a stage whose page exists links to it. Last, every other page in `docs/owner/` (not the index, not `stages/`), by its title. Run it whenever this skill changes `CLAUDE.md` or `docs/plan.md`, and commit the result with them. Never write the index by hand.
- **Sources**: issues of the stage, `docs/decisions.md`, the decision comments in those issues (`issues-workflow.md`), the source for sections 4 and 5, design boards, experiment docs, git. Every claim names its source.
- **Sections, top to bottom.** Short on top, deeper below; sections 3 to 8 open in `<details>`.
  1. What changed, and how to see or try it yourself: the command, the URL or the screen.
  2. The goal and `Done when`, with the evidence that it holds.
  3. Tasks: what was done, one line each, with the issue and the commit.
  4. Decisions made without the owner: each with one line why. Mark the ones worth a second look.
  5. Notable review findings: interesting points from reviewers and critics, and whether each was accepted or rejected.
  6. Architecture and design: decisions, boards, screenshots.
  7. Experiment results and cost.
  8. Open questions left for later.
- **Address**: `https://<tailnet host>/<project>/`, with the trailing slash, which serves `docs/owner/`. Links inside the pages are relative.
- **Setup, once per project**:
  - A git `post-commit` hook copies `docs/owner/` to `~/Library/Application Support/svop/<project>/owner/` (`rsync -a`, no delete: stage pages are never removed). launchd's python3 can read that folder on any Mac, while a project on an external volume or in a protected folder is blocked without a manual privacy grant.
  - A launchd agent `svop.<project>.owner-pages` (`~/Library/LaunchAgents/`, `RunAtLoad` and `KeepAlive` true) runs `/usr/bin/python3 -m http.server <port> --bind 127.0.0.1 --directory "<home>/Library/Application Support/svop/<project>/owner"`.
  - `tailscale serve --bg --set-path /<project> http://127.0.0.1:<port>`. If `tailscale` is not on PATH, use `/Applications/Tailscale.app/Contents/MacOS/Tailscale`. The tailnet needs HTTPS certificates on.
  - The tailnet host is `Self.DNSName` from `tailscale status --json`, without the final dot.
  - Write the address and the port at the top of `docs/plan.md`.
- **Check before sending**: fetch the stage page and the index through the tailnet address. Each must answer and show what you wrote (the stage name and the commit at the top). If a check fails, say the link is not checked.

## review

A piece of work closed with a result, such as an experiment.

1. Does the result change the plan: a goal, a stage, its `Done when`, a decision?
2. Yes: **fold** it as input, naming the result as the source.
3. No: nothing to do.
