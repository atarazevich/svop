---
name: plan
description: Keep the project plan (Goals, Stages, Decisions, Story in CLAUDE.md) current. Use for fold (owner input that is an idea, refinement or change of direction), next ("continue", "next", "погнали дальше"), and review (a piece of work closed with a result). Triggers come from rules/plan.md.
---

# Plan

The plan is four sections of the project's `CLAUDE.md`: Goals, Stages, Decisions, Story. The Decisions section lists the decisions in force, one line each; `docs/decisions.md` keeps each decision's context and the replaced ones. History is git of both. No other storage.

## Stages format

Each stage, in order:

```
### <n>. <name> — <done | current | next | later>
- Goal: <one line: what this stage achieves>
- In it: <the problems or items, one line each, issue ids when they exist>
- Done when: <observable criteria>
```

- Exactly one stage is `current`. `Done when` is required: without it, **next** cannot tell whether a stage is finished. A stage without it gets one before anything else.
- Issues name their stage (a GitHub milestone, or `stage:` in an issue file). Closed issues are evidence; a stage is done only when its `Done when` holds.

## fold

The owner gave an idea, a refinement or a change of direction.

1. Read Stages, Decisions and `docs/decisions.md`.
2. Put the input where it belongs: an item in the right stage, a new stage (usually `later`), a changed `Done when`, or a Decision. Keep the owner's words.
3. If it contradicts a Decision in force or an entry in `docs/decisions.md`, do not decide. Ask the owner through the router (`confirm`): the old decision, the new input, your recommendation. Change nothing until the answer.
4. Otherwise commit `CLAUDE.md` (and a `docs/decisions.md` entry for a new decision), and tell the owner in one or two lines what changed, in the channel the input came from.

Fold plans; it never starts work.

## next

The owner said "continue", "next" or "погнали дальше".

1. Check the `current` stage against its `Done when`, with evidence (closed issues, results, commits).
2. Not met: tell the owner in one line what is missing, and continue that stage.
3. Met: mark it `done`, make the first `next` stage `current`, commit. No `next` stage left: ask the owner which `later` stage comes next.
4. Break the current stage into issues for development (`issues-workflow.md`), and send them to the teams (`team.md`).
5. Tell the owner in one line what starts.

## review

A piece of work closed with a result, such as an experiment.

1. Does the result change the plan: a goal, a stage, its `Done when`, a decision?
2. Yes: **fold** it as input, naming the result as the source.
3. No: nothing to do.
