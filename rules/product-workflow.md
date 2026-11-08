# Product Workflow

For a team whose row in teams.yaml lists `product`. It keeps Goals, Stages,
Decisions and Story in CLAUDE.md true. Every team, agent and subagent calibrates on them.
Without a product team, the orchestrator keeps them (`plan.md`).

## Who
- **product**: the only writer of the four sections.
- **Orchestrator**: forwards the owner's decisions; reports when a stage's issues are all closed.
- **communication**: reads Story; sends signals.
- **Owner**: decides, in the orchestrator chat or through the router.

## Where: four sections of CLAUDE.md
- **Goals**: what the project is for and for whom. Five lines at most.
- **Stages**: in the format of the `plan` skill, which product uses for fold, next and review.
- **Decisions**: the decisions in force, one line each, with the date. A replaced
  decision is deleted; git keeps the history.
- **Story**: who we write for, what we highlight, and why. Five lines at most.
Other sections of CLAUDE.md belong to whoever wrote them.

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
- Goals, decisions and Story live only in CLAUDE.md.
