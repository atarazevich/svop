# Monitor Workflow

For a team whose row in teams.yaml lists `monitor`. It catches production problems and hands them to the team that owns them, before the owner notices.

## Who
- **monitor**: watches, groups, tickets, routes and follows up.
- **The owning team**: fixes the problem through its own workflows.
- **Orchestrator**: gets only what no team clearly owns, or what the owner must decide.

## Where
- A read-only watcher on the server records failures, error traces, restarts, low disk and checks that went overdue. It keeps recording while your computer sleeps.
- Tickets are issues (`issues-workflow.md`) in the area of the team that owns the cause.

## Steps
1. **Poll.** The monitor session reads the watcher every minute and looks only at what is new.
2. **Group.** Many failures with one cause are one incident.
3. **Ticket.** If an issue for the cause exists, add a comment. If not, open one: What, How it fits, Done when. Facts only.
4. **Route.** Send `new task: #N` to the team that owns the area.
5. **Close the loop.** Check that the failure stopped after the team's fix, then record the incident as closed.
6. **Escalate** to the orchestrator only when no team clearly owns the problem, or the owner must decide.

## Rules
- Read only: never change code, deploy, restart or approve anything.
