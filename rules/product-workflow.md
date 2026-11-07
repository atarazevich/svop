# Product Workflow

For a team whose row in teams.yaml lists `product`. It keeps Goals, Stages,
Decisions and Story in CLAUDE.md true. Every team, agent and subagent calibrates on them.

## Who
- **product**: the only writer of the four sections.
- **Orchestrator**: forwards the owner's decisions; reports when a stage's issues are all closed.
- **communication**: reads Story; sends signals.
- **Owner**: decides, in the orchestrator chat or through the router.

## Where: four sections of CLAUDE.md
- **Goals**: what the project is for and for whom. Five lines at most.
- **Stages**: in order. Each has a status (next, in progress, done) and Done when.
  Each issue names its stage (a GitHub milestone, or `stage:` in an issue file).
- **Decisions**: the decisions in force, one line each, with the date. A replaced
  decision is deleted; git keeps the history.
- **Story**: who we write for, what we highlight, and why. Five lines at most.
Other sections of CLAUDE.md belong to whoever wrote them.

## Steps
1. **Decision.** When: the orchestrator sends `decision: <text>`. Update CLAUDE.md,
   commit, reply `done: <commit>`.
2. **Stage done.** When: the orchestrator sends `stage done: <stage>` (every issue of
   the stage is closed). Mark the stage done, set the next one in progress, commit.
3. **Signal.** When: communication sends `signal: ...`. If a goal or a decision should
   change, open a router `confirm` with your recommendation as the first option.
   After the owner answers, go to step 1.
4. **Story.** When: the orchestrator forwards the owner's answer to communication's
   "Story needed". Write Story from the owner's words, commit. Never invent it.

## Rules
- Never change a goal, a decision or Story on your own judgment.
- Goals, decisions and Story live only in CLAUDE.md.
