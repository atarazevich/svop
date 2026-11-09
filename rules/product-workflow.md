# Product Workflow

For a team whose row in teams.yaml lists `product`. It keeps the plan (`docs/plan.md`)
and the Goal, About, Principles, Decisions, Story and Current stage sections of CLAUDE.md true
(the CLAUDE.md contract, `knowledge.md`). Every team, agent and subagent calibrates on them.
Without a product team, the orchestrator keeps them (`plan.md`).

## Who
- **product**: the only writer of the plan and those sections.
- **Orchestrator**: forwards the owner's decisions; reports when a stage's issues are all closed.
- **communication**: reads the Goal and Story; sends signals.
- **Owner**: decides, in the orchestrator chat or through the router.

## Where
- `docs/plan.md`: the stages, in the format of the `plan` skill.
- `CLAUDE.md`: the sections of the contract in `knowledge.md`.

## Steps
1. **Plan.** When: the orchestrator sends `plan: <words>` (the triggers in `plan.md`).
   Run the `plan` skill: fold, next or review. Reply `done: <commit>` or the question
   you asked the owner.
2. **Signal.** When: communication sends `signal: ...`. If a goal or a decision should
   change, open a router `confirm` with your recommendation as the first option.
   After the owner answers, fold it (step 1).
3. **Story.** When: the orchestrator forwards the owner's answer to communication's
   "Story needed". Write Story from the owner's words, commit. Never invent it.

## Rules
- Never change a goal, a decision or Story on your own judgment.
- The plan lives only in `docs/plan.md`; decisions in force and Story only in CLAUDE.md.
