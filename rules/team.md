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
3. **Teams**: one session per area of the project. A team runs the workflows its row lists, through subagents.
4. **Subagents**: `Explore`, `developer`, `code-reviewer`, `bloat-reviewer`, `ponytail-reviewer`, `designer`, `design-critic`. All code is written here.

## Teams

The only list of teams is `.claude/teams.yaml`. A small project has one team.

- `version`, `project`: the file format and the name of the project folder.
- `orchestrator: {session}`: the orchestrator's session name. The orchestrator has no role folder; the base rules are its role.
- `teams`: one row per area, with these fields:
  - `name`: the team's name.
  - `owns`: the folders or area it owns.
  - `boundary`: what it never does.
  - `workflows`: the processes it runs. Each name maps to `.claude/rules/<name>-workflow.md`. All rules load in every session; this list says which ones the team runs.
  - `status`: `active` or `paused`. A paused team has no tab.

Each team also has a folder `.claude/teams/<name>/` with `role.md`. The role holds only what no workflow and no row says.

## Names

These are derived from the row and are never written down:

- **Orchestrator**: session from `orchestrator.session`, tab label `★ orchestrator`.
- **Team**: session `<name>`, tab label `◇ <name>`, role file `.claude/teams/<name>/role.md`. The owner may look in but never has to follow it.
- A tab with no mark is the owner's own and not part of the harness.

`<project>` is the name of the project folder.

## How work moves

`SendMessage` is Claude Code's built-in messaging between sessions on the same machine. A session is addressed by the name it was started with (`claude -n <name>`).

- Work for a team is a `ready` issue (`issues-workflow.md`) plus one message to the team's session: `SendMessage` to `<name>`, text `new task: #N`. Research needs no issue.
- A team reports to the orchestrator's session (`orchestrator.session`) the same way, with one of three messages:
  - **done**: the commit hash.
  - **blocked**: what was tested, what failed, the one step needed.
  - **question**: the question and the team's recommendation.
- Teams talk to the orchestrator, never to the owner. If the owner types in a team's tab, the team answers there, briefly, and goes on.
- When every issue of a stage is closed, the orchestrator sends `stage done: <stage>` to `product`, only if a product team exists.
- Work stays with the team that owns its area. To go faster, a team runs subagents in parallel, or the orchestrator starts a second session of the same team (`<name>-2`).

## Setting up the harness

When the owner says "set up the harness", the session that hears it does these steps, in order:

1. **Check the tools and the repository.** `claude --version`, `herdr --version`, `gh auth status`. If a tool is missing or `gh` is not logged in, follow steps 3 and 4 of SVOP's `INSTALL.md` (in `~/.svop`), then continue. If `git config user.name` or `user.email` is empty, set them as in step 5 of SVOP's `INSTALL.md` before any commit. If the folder is not a git repository, run `git init`. If it has no commits, make a first commit. If it has no GitHub remote (`gh repo view` fails), ask the owner whether to keep the issues local. Local: issues use file mode (`issues-workflow.md`, `docs/issues/`); skip `gh repo create` and step 3. Otherwise run `gh repo create <folder name> --private --source . --push`.
2. **Check the files.** In this project's `.claude/`: the six agents are in `agents/`. `team.md`, `orchestration.md`, `knowledge.md`, `worktrees.md` and the `*-workflow.md` files are in `rules/`. `grill` is in `skills/`. If one is missing, stop and name it.
3. **Create the labels**, if they do not exist (GitHub mode only):
   ```
   gh label create idea --color FBCA04 --description "Needs exploration"
   gh label create ready --color 0E8A16 --description "Scoped, executable"
   ```
4. **Write the registry.** Read `CLAUDE.md` and the top-level folders, then pick the template in `~/.svop/templates/` that fits: `web-service.yaml` (backend, agent, dashboard, monitor), `app.yaml` (app, site) or `start-small.yaml` (one `build` team). Ask the owner one question: name the three templates in one line each, say which you recommend and why. Recommend by what `CLAUDE.md` describes; when unsure, recommend `start-small.yaml`. Copy the chosen template to `.claude/teams.yaml`, set `project` and `orchestrator.session` (`<project>-orchestrator` by default), and map each row's `owns` to the real folders. For each row, copy `~/.svop/teams/<name>/` to `.claude/teams/<name>/`. Then check: every team has `teams/<name>/role.md`, and every name in `workflows:` has `rules/<name>-workflow.md`. If one is missing, stop and name it. Commit `teams.yaml`, the team folders and the rules together in one commit, then push if there is a remote.
5. **Check herdr is running.** `herdr status`. If no server runs, ask the owner to open herdr in a terminal.
6. **Start the sessions** in herdr. Every herdr command prints JSON. First run `herdr workspace list` and look for a workspace whose `label` is `<project>`; use its `workspace_id`. If there is none, create it and read `workspace_id` from the output. For each tab, the new pane id is `result.root_pane.pane_id` in the output of `herdr tab create`.

```
herdr workspace create --label <project> --cwd <project path>          # only if none has this label
herdr tab create --workspace <workspace id> --cwd <project path> --label "★ orchestrator"
herdr pane run <pane id> "claude -n <orchestrator.session>"
herdr tab create --workspace <workspace id> --cwd <project path> --label "◇ <name>"
herdr pane run <pane id> "claude -n <name> --append-system-prompt-file .claude/teams/<name>/role.md --permission-mode bypassPermissions --settings '{\"autoCompactEnabled\":true,\"outputStyle\":\"default\"}'"
```

Repeat the last two lines for each `active` team in `teams.yaml`. Teams start with auto-compact on and without permission prompts, because they run long without the owner. The orchestrator keeps the owner's own settings.

7. **Check the sessions.** Run `ListAgents`. The orchestrator and every team must appear by name. If one is missing, read its pane (`herdr pane read <pane id>`) and fix it.
8. **Hand over.** Tell the owner to switch to the `★ orchestrator` tab and talk only there.

To restart after a crash, run step 6 again; use `--resume <session id>` in place of `-n <name>` (keep the other flags) to keep a session's history.

Status: `herdr agent list`, `herdr pane read <pane id>`.

## Add or pause a team

- **Add.** Add a row to `teams.yaml` and copy `~/.svop/teams/<name>/` to `.claude/teams/<name>/`. Start the tab as in step 6.
- The library also has `product` and `communication`, which no template includes. Their rows:
  ```yaml
  - name: product
    owns: Goals, Stages and Decisions in CLAUDE.md
    boundary: Writes no code and posts nothing in public. Changes a goal or a decision only after the owner says yes.
    workflows: [product]
    status: active

  - name: communication
    owns: docs/communication/
    boundary: Reads CLAUDE.md and never edits it. Posts nothing in public.
    workflows: [communication]
    status: active
  ```
  When product exists, every other row that owns `CLAUDE.md` gets the boundary "Never edits Goals, Stages or Decisions in CLAUDE.md".
- **Pause.** Set `status: paused` and close the team's tab.
- Commit the change.
