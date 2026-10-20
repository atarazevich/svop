# Team

## Why

One chat that does everything fills with execution. Then no room is left to think.

So the work is split into two spaces:
- **Discovery**: the owner and the orchestrator decide what is worth doing and define it as an issue.
- **Execution**: a team builds the defined issue.

Once an issue is defined, the owner stops following it. The harness carries it to done and reports back.

## Roles

1. **Owner**: the one human. Decides.
2. **Orchestrator**: the one session the owner talks to. It turns decisions into issues, sends each issue to the team that owns its area, and follows up. It answers the teams' simple questions itself and tells the owner after. It writes no code.
3. **Teams**: one session per area of the project. A team runs its issues through subagents (`development-workflow.md`, `design-workflow.md`).
4. **Subagents**: `Explore`, `developer`, `code-reviewer`, `bloat-reviewer`, `ponytail-reviewer`, `designer`, `design-critic`. All code is written here.

## Teams

Filled at setup from a template in `~/.svop/templates/`. One row per area. A small project has one team.

| Session and tab | Owns | Boundary |
|---|---|---|
| `<team>` | `<folders or area it owns, for example: web/ and its issues>` | `<what it never does>` |

## Names

- **Orchestrator**: session `<project>-orchestrator`, tab label `★ orchestrator`.
- **Team**: session `<team>`, tab label `◇ <team>`. The owner may look in but never has to follow it.
- A tab with no mark is the owner's own and not part of the harness.

`<project>` is the name of the project folder.

## How work moves

`SendMessage` is Claude Code's built-in messaging between sessions on the same machine. A session is addressed by the name it was started with (`claude -n <name>`).

- Work for a team is a `ready` issue (`github-issues.md`) plus one message to the team's session: `SendMessage` to `<team>`, text `new task: #N`. Research needs no issue.
- A team reports to `<project>-orchestrator` the same way, with one of three messages:
  - **done**: the commit hash.
  - **blocked**: what was tested, what failed, the one step needed.
  - **question**: the question and the team's recommendation.
- Teams talk to the orchestrator, never to the owner. If the owner types in a team's tab, the team answers there, briefly, and goes on.
- Work stays with the team that owns its area. To go faster, a team runs subagents in parallel, or the orchestrator starts a second session of the same team (`<team>-2`).

## Setting up the harness

When the owner says "set up the harness", the session that hears it does these steps, in order:

1. **Check the tools and the repository.** `claude --version`, `herdr --version`, `gh auth status`. If a tool is missing or `gh` is not logged in, follow steps 3 and 4 of SVOP's `INSTALL.md` (in `~/.svop`), then continue. If `git config user.name` or `user.email` is empty, set them as in step 5 of SVOP's `INSTALL.md` before any commit. If the folder is not a git repository, run `git init`. If it has no commits, make a first commit. If it has no GitHub remote (`gh repo view` fails), run `gh repo create <folder name> --private --source . --push`.
2. **Check the files.** The six agents are in `~/.claude/agents/`. `development-workflow.md`, `design-workflow.md`, `github-issues.md` and `knowledge.md` are in `~/.claude/rules/`. `team.md` and `worktrees.md` are in `.claude/rules/` of this project. If one is missing, stop and name it.
3. **Create the labels**, if they do not exist:
   ```
   gh label create idea --color FBCA04 --description "Needs exploration"
   gh label create ready --color 0E8A16 --description "Scoped, executable"
   ```
4. **Fill the Teams table.** Read `CLAUDE.md` and the top-level folders, then pick the template in `~/.svop/templates/` that fits: `web-service.md` (backend, agent, dashboard, monitor), `app.md` (app, site) or `start-small.md` (one `build` team). Ask the owner one question: name the three templates in one line each, say which you recommend and why. Recommend by what `CLAUDE.md` describes; when unsure, recommend `start-small.md`. Copy the chosen template's Teams table into this file, map each row's Owns to the real folders, and add the template's other sections below the table. Commit `team.md` and `worktrees.md` together in one commit, then push.
5. **Check herdr is running.** `herdr status`. If no server runs, ask the owner to open herdr in a terminal.
6. **Start the sessions** in herdr. Every herdr command prints JSON. First run `herdr workspace list` and look for a workspace whose `label` is `<project>`; use its `workspace_id`. If there is none, create it and read `workspace_id` from the output. For each tab, the new pane id is `result.root_pane.pane_id` in the output of `herdr tab create`.

```
herdr workspace create --label <project> --cwd <project path>          # only if none has this label
herdr tab create --workspace <workspace id> --cwd <project path> --label "★ orchestrator"
herdr pane run <pane id> "claude -n <project>-orchestrator"
herdr tab create --workspace <workspace id> --cwd <project path> --label "◇ <team>"
herdr pane run <pane id> "claude --permission-mode bypassPermissions --settings '{\"autoCompactEnabled\":true}' -n <team>"
```

Repeat the last two lines for each team. Teams start with auto-compact on and without permission prompts, because they run long without the owner. The orchestrator keeps the owner's own settings.

7. **Check the sessions.** Run `ListAgents`. The orchestrator and every team must appear by name. If one is missing, read its pane (`herdr pane read <pane id>`) and fix it.
8. **Hand over.** Tell the owner to switch to the `★ orchestrator` tab and talk only there.

To restart after a crash, run step 6 again; use `claude --resume <session id>` in place of `claude -n ...` to keep a session's history.

Status: `herdr agent list`, `herdr pane read <pane id>`.
