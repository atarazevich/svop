# Template: Web service

For a service that runs on a server: an API, an AI agent that talks to your users, and a dashboard for you. Four teams.

## Teams

| Session and tab | Owns | Boundary |
|---|---|---|
| `backend` | API, workers, database, deploys, every call to an outside service | The only code that writes to outside services. Other teams read through its API. |
| `agent` | The AI agent your users talk to: prompts, replies, the runtime | Never builds against guessed fields. The backend sends the contract first. |
| `dashboard` | Your own view of the service | Reads only. Anything it needs from the backend is an issue in the backend's area. |
| `monitor` | Production failures. Read-only | Never fixes, deploys or approves. Reads, groups, opens tickets, routes, follows up. |

## Rules for all teams

- Work for another team is an issue in that team's area, plus one message: `new task: #N`.
- Anything that changes what the AI agent sees or says is a short spec the owner approves first.

## The monitor

The monitor is a service, not a person watching logs. It catches production problems and hands them to the team that owns them, before the owner notices.

1. **Watch.** A read-only watcher on the server records failures, error traces, restarts, low disk and checks that went overdue. It keeps recording while your computer sleeps.
2. **Poll.** The monitor session reads the watcher every minute and looks only at what is new.
3. **Group.** Many failures with one cause are one incident.
4. **Ticket.** If an issue for the cause exists, it adds a comment. If not, it opens one: What, How it fits, Done when. Facts only.
5. **Route.** It sends `new task: #N` to the team that owns the area.
6. **Close the loop.** It checks the failure stopped after the team's fix, then records the incident as closed.
7. **Escalate** to the orchestrator only when no team clearly owns the problem, or the owner must decide.

The monitor never changes code, never deploys and never restarts anything.
