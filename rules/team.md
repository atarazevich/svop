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

- `version`, `project`: the file format (`2`) and the name of the project folder.
- `root` (optional): the project folder; default, the folder that holds `.claude/`.
- `repos` (optional): `{path, url}` pairs, `path` relative to `root`. `svop up` clones a missing one.
- `env_file` (optional): a `KEY=VALUE` file outside git, read as data (no shell) and given to every session's `claude` process only. Its values are never printed.
- `herdr: {space}`: the name of the Herdr app space the sessions show in; default, `project`.
- `claude` (optional): Claude Code flags for every session, passed through unchanged: `key: value` is `--key value`, `true` a bare flag, a list the flag's values, a mapping (e.g. `settings`, `mcp-config`) one JSON string. Relative paths are passed unchanged, so they resolve from the session's `cwd`.
- `orchestrator`: the orchestrator's `session` name, and like every team row `session_id`, `cwd` (relative to `root`), `herdr: {tab}` and `claude`. The orchestrator has no role folder; the base rules are its role.
- `teams`: one row per area, with these fields:
  - `name`: the team's name.
  - `owns`: the folders or area it owns.
  - `boundary`: what it never does.
  - `workflows`: the processes it runs. Each name maps to `.claude/rules/<name>-workflow.md`. All rules load in every session; this list says which ones the team runs.
  - `schedule` (optional): `"HH:MM"`, local time, once a day, e.g. `"10:07"`. A scheduled team has no tab: launchd starts one headless pass a day at that time (setup step 6).
  - `status`: `active` or `paused`. A paused team has no tab and no launchd agent.
  - `session_id` (optional): the chat to resume. Present: the session starts with `--resume <id>`, and if that chat has no transcript in its `cwd`, start stops with an error instead of starting fresh. Absent: the first start makes one and writes it here.
  - `cwd` (optional): the session's folder, relative to `root`; default `.`.
  - `herdr: {tab}`: the tab label.
  - `claude`: the session's own flags, merged over the project's key by key. A team's include `append-system-prompt-file: .claude/teams/<name>/role.md`. The templates set the models: the orchestrator runs on `model: fable`, each team on `model: opus` with `effort: medium`. Change them in the row.

Each team also has a folder `.claude/teams/<name>/` with `role.md`. The role holds only what no workflow and no row says.

## Names

- **Orchestrator**: session from `orchestrator.session`, tab label `★ orchestrator`.
- **Team**: session `<name>`, tab label `◇ <name>`, role file `.claude/teams/<name>/role.md`. The owner may look in but never has to follow it.
- The session name is passed as `-n`. Its `hc` terminal is named `<project>-<session>` (once, if the session name already starts with `<project>-`), which must be 1-32 of `a-z 0-9 - _`. A row without `herdr: {tab}` gets the label above.
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
- Work stays with the team that owns its area. To go faster, a team runs subagents in parallel, or the orchestrator starts a second session of the same team (`<name>-2`).

## Setting up the harness

When the owner says "set up the harness", the session that hears it does these steps, in order:

1. **Check the tools and the repository.** `claude --version`, `hc --version`, `uv --version`, `svop --help`, `gh auth status`. If a tool is missing or `gh` is not logged in, follow steps 2 to 4 of SVOP's `INSTALL.md` (in `~/.svop`), then continue. If `git config user.name` or `user.email` is empty, set them as in step 5 of SVOP's `INSTALL.md` before any commit. If the folder is not a git repository, run `git init`. If it has no commits, make a first commit. If it has no GitHub remote (`gh repo view` fails), ask the owner whether to keep the issues local. Local: issues use file mode (`issues-workflow.md`, `docs/issues/`); skip `gh repo create` and step 3. Otherwise run `gh repo create <folder name> --private --source . --push`.
2. **Check the files.** In this project's `.claude/`: the six agents are in `agents/`. `team.md`, `orchestration.md`, `knowledge.md`, `git.md`, `plan.md` and the `*-workflow.md` files are in `rules/`. `grill` and `plan` are in `skills/`. If one is missing, stop and name it.
3. **Create the labels**, if they do not exist (GitHub mode only):
   ```
   gh label create idea --color FBCA04 --description "Needs exploration"
   gh label create ready --color 0E8A16 --description "Scoped, executable"
   ```
4. **Write the registry.** Read `CLAUDE.md` and the top-level folders, then pick the template in `~/.svop/templates/` that fits: `web-service.yaml` (backend, agent, dashboard, monitor), `app.yaml` (app, site) or `start-small.yaml` (one `build` team). Ask the owner one question: name the three templates in one line each, say which you recommend and why. Recommend by what `CLAUDE.md` describes; when unsure, recommend `start-small.yaml`. Copy the chosen template to `.claude/teams.yaml`, set `project`, `herdr.space` and `orchestrator.session` (`<project>-orchestrator` by default), and map each row's `owns` to the real folders. If the project has a remote, add it under `repos` as `{path: ., url: github.com/<owner>/<repo>}`. If sessions of this project already run, record each one's id as its `session_id` (the `sessionId` in `~/.claude/sessions/<pid>.json` whose `name` and `cwd` match). For each row, copy `~/.svop/teams/<name>/` to `.claude/teams/<name>/`. Then check: every team has `teams/<name>/role.md`, and every name in `workflows:` has `rules/<name>-workflow.md`. If one is missing, stop and name it. Commit `teams.yaml`, the team folders and the rules together in one commit, then push if there is a remote.
5. **Check the core and the window.** `hc server status` must show a core; if none runs, `hc server start`. The window is optional: `herdr-app ls` answers when the Herdr app is open. If it does not, tell the owner in one line that the sessions will run without a window until they open Herdr.
6. **Start the sessions**: `svop up <project>`. It clones missing `repos` and starts the orchestrator and every `active` team without a `schedule`, each in its own `hc` terminal, with the flags from `teams.yaml`. When the Herdr app is open, each terminal shows in the project's space (made if missing) under its tab label; with no window they run all the same, and `svop` says so in one line. `--dry-run` prints the commands and runs nothing. On a session's first start, if Claude Code asks whether to trust its folder, `svop` answers yes, and only for a folder inside the project root. For a session started with `dangerously-load-development-channels`, it confirms "I am using this for local development" under the same limit. `svop` answers only before Claude Code runs, never into a running chat. Teams start with auto-compact on and without permission prompts, because they run long without the owner. The orchestrator keeps the owner's own settings.

For each `active` team with a `schedule`, write `~/Library/LaunchAgents/svop.<project>.<name>.plist` and load it; it gets no tab. In `StartCalendarInterval`, `Hour` and `Minute` are the row's `"HH:MM"`. Find the path of `claude` with `command -v claude`; `PATH` must hold the folders of `claude`, `gh` and `bus`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>svop.<project>.<name></string>
  <key>WorkingDirectory</key><string><project path></string>
  <key>ProgramArguments</key><array>
    <string><path of claude></string><string>-p</string>
    <string>Run your daily pass (<name>-workflow.md).</string>
    <string>--append-system-prompt-file</string><string>.claude/teams/<name>/role.md</string>
    <string>--permission-mode</string><string>bypassPermissions</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string><folders of claude, gh, bus>:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer><HH></integer><key>Minute</key><integer><MM></integer></dict>
  <key>StandardOutPath</key><string><home>/Library/Logs/svop/<project>-<name>.log</string>
  <key>StandardErrorPath</key><string><home>/Library/Logs/svop/<project>-<name>.log</string>
</dict></plist>
```

```
mkdir -p ~/Library/Logs/svop
plutil -lint ~/Library/LaunchAgents/svop.<project>.<name>.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/svop.<project>.<name>.plist
```

launchd does not read `~/.zshrc`, and the job must not get `ANTHROPIC_API_KEY`: with it set, `claude -p` drops the claude.ai connectors (Google Drive). The job uses the owner's claude.ai login, so when that login ends, the passes fail until the owner logs in again.

7. **Check the sessions.** Run `ListAgents`. The orchestrator and every team without a `schedule` must appear by name. If one is missing, read its terminal (`hc read <project>-<session> --lines 40`) and fix it. For each scheduled team, `launchctl print gui/$(id -u)/svop.<project>.<name>` must show the job.
8. **Hand over.** Tell the owner to switch to the `★ orchestrator` tab and talk only there.

To restart after a crash or a reboot, run `svop up <project>` again: live sessions are left alone, the others resume from their `session_id`, each in a tab with its label. One session: `svop start <project> <session>`.

`svop stop <project> <session>` types `/exit` into the session's terminal only when its status is idle or done, and never kills a process. It types `/exit` into the tab, so a draft left unsent there is sent with it. A session resumed and not used since reports no status, so `svop stop` refuses it: type `/exit` in its tab.

Status: `hc ls`, `hc get <project>-<session>`, `hc read <project>-<session>`.

**A project on a server.** `svop` runs on the machine that holds the project folder. From the owner's machine (`hc machine ls` lists the servers):
1. Start: `hc run --on <machine> --cwd <project folder> -- sh -lc "svop up ."`. It shows what `svop` prints. If it ends with `still running as <machine>/<t>`, `svop` goes on: `hc wait <machine>/<t>`, then `hc read <machine>/<t>` and `hc rm <machine>/<t>`. The server has no window, so the terminals run unseen.
2. Show: `herdr-app do space.new --name <project> --machine <machine> --folder <project folder>`. It prints the space, its first tab and that tab's shell, each as `<machine>/<id>`.
3. For each session: `hc label <machine>/<project>-<session> herdr.space=<space id without "<machine>/">`. It shows as a new tab; name it with `herdr-app do tab.rename --id <its tab id> --name "<label>"` (`herdr-app ls` gives the id). Then close the first tab's shell: `hc kill <machine>/<shell>`.

## Add or pause a team

- **Add.** Add a row to `teams.yaml` and copy `~/.svop/teams/<name>/` to `.claude/teams/<name>/`. Start it with `svop start <project> <name>`.
- The library also has `product` and `communication`, which no template includes. Their rows:
  ```yaml
  - name: product
    owns: docs/plan.md and the CLAUDE.md contract sections (knowledge.md)
    boundary: Writes no code and posts nothing in public. Changes a goal, a decision or Story only after the owner says yes.
    workflows: [product]
    status: active
    herdr: {tab: "◇ product"}
    claude:
      append-system-prompt-file: .claude/teams/product/role.md
      permission-mode: bypassPermissions
      settings: {autoCompactEnabled: true, outputStyle: default}

  - name: communication
    owns: docs/communication/
    boundary: Reads CLAUDE.md and never edits it. Posts nothing in public.
    workflows: [communication]
    schedule: "10:07"
    status: active
  ```
  When product exists, no other row edits `docs/plan.md` or `CLAUDE.md`.
- **Pause.** Set `status: paused` and run `svop stop <project> <name>` (if it refuses, see `svop stop` above). Its terminal ends and its tab closes. A scheduled team: `launchctl bootout gui/$(id -u)/svop.<project>.<name>`, then `launchctl disable gui/$(id -u)/svop.<project>.<name>` so it does not start again at login. To resume: `launchctl enable` with the same target, then `launchctl bootstrap` as in step 6, and set `status: active`.
- Commit the change.
