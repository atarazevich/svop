# Product Workflow

For a team whose row in teams.yaml lists `product`. It keeps Goals, Stages and
Decisions in CLAUDE.md true. Every team, agent and subagent calibrates on them.

## Who
- **product**: the only writer of the three sections.
- **Orchestrator**: forwards the owner's decisions; reports when a stage's issues are all closed.
- **communication**: sends signals.
- **Owner**: decides, in the orchestrator chat or through the router.

## Where: three sections of CLAUDE.md
- **Goals**: what the project is for and for whom. Five lines at most.
- **Stages**: in order. Each has a status (next, in progress, done) and Done when.
  Each issue names its stage (a GitHub milestone, or `stage:` in an issue file).
- **Decisions**: the decisions in force, one line each, with the date. A replaced
  decision is deleted; git keeps the history.
Other sections of CLAUDE.md belong to whoever wrote them.

## Steps
1. **Decision.** When: the orchestrator sends `decision: <text>`. Update CLAUDE.md,
   commit, reply `done: <commit>`. A stage added or changed → `stage planned: <stage>`
   to communication.
2. **Stage done.** When: the orchestrator sends `stage done: <stage>` (every issue of
   the stage is closed). Mark the stage done, set the next one in progress, commit,
   send `stage done: <stage>` to communication.
3. **Signal.** When: communication sends `signal: ...`. If a goal or a decision should
   change, open a router `question` with your recommendation as the first option.
   After the owner answers, go to step 1.

## Rules
- Never change a goal or a decision on your own judgment.
- Goals and decisions live only in CLAUDE.md.
