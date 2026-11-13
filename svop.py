#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Start and stop a project's Claude Code sessions in herdr-core (`hc`), as `.claude/teams.yaml` (version 2) says.
Each session runs in an hc terminal named after it. When the Herdr app answers, the terminals show in the project's
space; with no window they run all the same.

Usage:
  svop up <project> [--dry-run]              clone missing repos, start every active session that has no schedule
  svop start <project> <session> [--dry-run] start one session; a live one is left alone
  svop stop <project> <session>              type /exit into the session's terminal, only when it is idle or done

<project> is a name from the Router registry cache (~/.cache/router/projects.json) or a path to a project
folder. <session> is `orchestrator.session` or a team's `name`. The file format is in rules/team.md.
"""
import argparse
import glob
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from typing import Callable, Dict, List, NamedTuple, Optional

import yaml

REGISTRY = "~/.cache/router/projects.json"
SELF = os.path.realpath(__file__)
TRUST_YES = "Yes, I trust this folder"  # options of Claude Code's first-start dialogs
CHANNELS_YES = "I am using this for local development"
OTHER = {TRUST_YES: "No, exit", CHANNELS_YES: "Exit"}  # the option each dialog starts on or offers beside
WAIT = 30  # seconds a session gets to come up, and the window to show its terminal


class Fail(Exception):
    pass


class Session(NamedTuple):
    name: str
    sid: Optional[str]
    cwd: str
    tab: str
    claude: Dict
    orchestrator: bool
    active: bool
    schedule: Optional[str]


def project_dir(arg: str) -> str:
    path = os.path.expanduser(arg)
    if os.path.isdir(path):
        return os.path.abspath(path)
    try:
        with open(os.path.expanduser(REGISTRY), encoding="utf-8") as f:
            projects = json.load(f)["projects"]
    except (OSError, ValueError, KeyError) as e:
        raise Fail(f"{arg} is not a folder, and the registry cache {REGISTRY} is not usable ({type(e).__name__})")
    for p in projects:
        if p.get("name") == arg and p.get("folder"):
            return p["folder"]
    raise Fail(f"{arg} is neither a folder nor a project in {REGISTRY}")


def read_env(path: str) -> Dict[str, str]:
    """KEY=VALUE lines, `#` comments, values optionally in matching quotes. Read as data; no shell. Errors never
    show a value."""
    env = {}
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        raise Fail(f"env_file {path} cannot be read")
    for n, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", line)
        if not m:
            raise Fail(f"env_file {path}, line {n}: not KEY=VALUE")
        value = m.group(2)
        if value[:1] in "'\"" and len(value) >= 2 and value[-1] == value[0]:
            value = value[1:-1]
        elif value[:1] in "'\"":
            raise Fail(f"env_file {path}, line {n} ({m.group(1)}): unclosed quote")
        env[m.group(1)] = value
    return env


def load(folder: str) -> Dict:
    path = os.path.join(folder, ".claude", "teams.yaml")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except OSError:
        raise Fail(f"no {path}")
    if not isinstance(cfg, dict) or cfg.get("version") != 2:
        raise Fail(f"{path} is not version 2; add the version 2 fields (rules/team.md, Teams)")
    cfg["_path"] = path
    cfg["_root"] = os.path.abspath(os.path.expanduser(cfg.get("root") or folder))
    if cfg.get("env_file"):
        cfg["_env_file"] = os.path.expanduser(cfg["env_file"])
        cfg["_env_names"] = sorted(read_env(cfg["_env_file"]))
    return cfg


def sessions(cfg: Dict) -> List[Session]:
    """The orchestrator, then the teams. Session-level `claude:` keys override project-level ones, key by key."""
    base = cfg.get("claude") or {}

    def make(row: Dict, name: str, tab: str, orchestrator: bool) -> Session:
        return Session(name=name, sid=row.get("session_id"),
                       cwd=os.path.normpath(os.path.join(cfg["_root"], os.path.expanduser(row.get("cwd") or "."))),
                       tab=(row.get("herdr") or {}).get("tab") or tab, claude={**base, **(row.get("claude") or {})},
                       orchestrator=orchestrator, active=orchestrator or row.get("status") == "active",
                       schedule=row.get("schedule"))

    orch = cfg.get("orchestrator") or {}
    out = [make(orch, orch["session"], "★ orchestrator", True)] if orch.get("session") else []
    return out + [make(t, t["name"], f"◇ {t['name']}", False) for t in cfg.get("teams") or []]


def flags(claude: Dict) -> List[str]:
    """Claude Code flags, passed through: `key: value` → --key value, true → --key, false → nothing,
    a list → the flag's values, a mapping → one JSON string. A string starting with ~ is a home path."""
    out: List[str] = []
    for key, value in claude.items():
        if value is False or value is None:
            continue
        out.append(f"--{key}")
        if value is True:
            continue
        for v in value if isinstance(value, list) else [value]:
            if isinstance(v, dict):
                out.append(json.dumps(v, separators=(",", ":")))
            else:
                v = str(v)
                out.append(os.path.expanduser(v) if v.startswith("~") else v)
    return out


def command(cfg: Dict, s: Session, sid: str, resume: bool) -> List[str]:
    line = ["claude", "-n", s.name, "--resume" if resume else "--session-id", sid, *flags(s.claude)]
    # With an env_file, svop itself starts claude with those variables, so they reach only claude: never the
    # terminal's shell, its history, or a command line.
    return [SELF, "--with-env", cfg["_env_file"], "--", *line] if cfg.get("_env_file") else line


def transcript(cwd: str, sid: str) -> Optional[str]:
    """Claude Code keeps a chat at ~/.claude/projects/<cwd, every non-alphanumeric char as '-'>/<id>.jsonl."""
    root = os.path.expanduser("~/.claude/projects")
    for p in dict.fromkeys([os.path.realpath(cwd), cwd]):
        path = os.path.join(root, re.sub(r"[^a-zA-Z0-9]", "-", p), f"{sid}.jsonl")
        if os.path.isfile(path):
            return path
    return None


def live(s: Session) -> Optional[str]:
    """Id of a running Claude Code chat that is this session: a ~/.claude/sessions/<pid>.json with its id, or its
    name in its folder, whose pid runs and started at the file's procStart (a reused pid started later)."""
    for path in glob.glob(os.path.expanduser("~/.claude/sessions/*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            same = (s.sid and data.get("sessionId") == s.sid) or (
                data.get("name") == s.name and os.path.realpath(data.get("cwd", "")) == os.path.realpath(s.cwd))
            if not same:
                continue
            pid, start = int(data["pid"]), data.get("procStart")
            os.kill(pid, 0)
            ps = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True).stdout
            if not isinstance(start, str) or start.split() == ps.split():
                return data["sessionId"]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    return None


def write_id(cfg: Dict, s: Session, sid: str, write: bool) -> None:
    """Insert `session_id: <sid>` into the session's own block, keeping the rest of the file as it is. The result
    is parsed again and must give this session this id; else nothing is written. `write=False` only checks."""
    with open(cfg["_path"], encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)
    if s.orchestrator:
        top = next((i for i, l in enumerate(lines) if re.match(r"orchestrator:\s*(#.*)?$", l)), None)
        block = []
        for i in range(top + 1 if top is not None else len(lines), len(lines)):
            if lines[i].strip() and not lines[i][0].isspace():
                break
            block.append(i)
        hit = next((i for i in block if re.match(r"(\s+)session:", lines[i])), None)
        indent = "" if hit is None else re.match(r"\s*", lines[hit]).group()
    else:
        name = re.compile(rf"(\s*)- name:\s*['\"]?{re.escape(s.name)}['\"]?\s*(#.*)?$")
        hit = next((i for i, l in enumerate(lines) if name.match(l)), None)
        indent = "" if hit is None else name.match(lines[hit]).group(1) + "  "
    if hit is not None:
        lines[hit] = lines[hit] if lines[hit].endswith("\n") else lines[hit] + "\n"
        lines.insert(hit + 1, f"{indent}session_id: {sid}\n")
        text = "".join(lines)
        try:
            written = {x.name: x.sid for x in sessions({**yaml.safe_load(text), "_root": cfg["_root"]})}
        except (yaml.YAMLError, KeyError, TypeError, AttributeError):
            written = {}
        if written.get(s.name) == sid:
            if write:
                with open(cfg["_path"], "w", encoding="utf-8") as f:
                    f.write(text)
            return
    raise Fail(f"{s.name} has no session_id, and one cannot be written into {cfg['_path']}: write its entry in "
               f"block form (one key per line), or add `session_id: <uuid>` by hand. Not started")


def tool(*args: str) -> str:
    try:
        out = subprocess.run(args, capture_output=True, text=True)
    except OSError as e:
        raise Fail(f"{args[0]}: {e.strerror}")
    if out.returncode != 0:
        raise Fail(f"{shlex.join(args)}: {out.stderr.strip() or out.stdout.strip()}")
    return out.stdout


def call(dry: bool, *cmd: str) -> Dict:
    """Run an `hc` or `herdr-app` command and read its JSON, or with `dry` only print it."""
    if dry:
        print(shlex.join(cmd))
        return {}
    return json.loads(tool(*(cmd[:2] + ("--json",) + cmd[2:] if cmd[0] == "hc" else cmd)))


def terminal(name: str) -> Optional[Dict]:
    """The hc terminal with this name: the live one, else the last finished one; None if there is none."""
    try:
        return call(False, "hc", "get", name)
    except Fail as e:
        if "not_found" in str(e):
            return None
        raise


def window() -> Optional[Dict]:
    """The Herdr app's spaces, tabs and terminals; None when no window answers."""
    try:
        return call(False, "herdr-app", "ls")
    except (Fail, ValueError):
        return None


def find(layout: Optional[Dict], key: str, value: str) -> Optional[Dict]:
    """A space of this machine in the window by `id` or `name`."""
    return next((x for x in (layout or {}).get("spaces", []) if x.get(key) == value and not x.get("machine")), None)


def poll(check: Callable[[], Optional[str]]) -> Optional[str]:
    """`check` every half second until it gives something, for at most WAIT seconds."""
    end = time.monotonic() + WAIT
    while time.monotonic() < end:
        found = check()
        if found is not None:
            return found
        time.sleep(0.5)
    return None


def check_names(cfg: Dict) -> None:
    """Every session's hc terminal name is valid and this project's names are distinct, before anything starts."""
    seen: Dict[str, str] = {}
    for s in sessions(cfg):
        name = term(cfg, s)
        if name in seen:
            raise Fail(f"{seen[name]} and {s.name} both give the hc terminal name {name}; rename one in {cfg['_path']}")
        seen[name] = s.name


def term(cfg: Dict, s: Session) -> str:
    """The session's hc terminal name: `<project>-<session>`. hc names are unique among a machine's live terminals,
    but two projects can still map to one name (project `a`, session `b-c`; project `a-b`, session `c`)."""
    project = cfg.get("project")
    name = s.name if s.name.startswith(f"{project}-") else f"{project}-{s.name}"
    if not re.fullmatch(r"[a-z0-9_-]{1,32}", name):
        raise Fail(f"{s.name}: its hc terminal name {name} must be 1-32 of a-z 0-9 - _; shorten or rename the session "
                   f"or `project` in {cfg['_path']}")
    return name


def dialog(screen: str, pick: str, other: str) -> Optional[bool]:
    """None if this first-start dialog of Claude Code is not on screen; else whether its marker is on `pick`. The
    dialog counts only as its own frame: both options and the hint, each at the start of its own line, and its marker
    the only ❯ on screen (a running session always shows ❯ at its prompt)."""
    def line(text: str) -> Optional[re.Match]:
        return re.search(rf"^[ \t]*(❯[ \t]*)?(?:\d+\.[ \t]*)?{re.escape(text)}[ \t]*$", screen, re.M)

    yes, no = line(pick), line(other)
    if not (yes and no and screen.count("❯") == 1 and re.search(r"^[ \t]*Enter to confirm\b", screen, re.M)):
        return None
    return bool(yes.group(1))


def answer(cfg: Dict, s: Session, name: str, wanted: Dict[str, str]) -> None:
    """Answer the first-start dialogs in `wanted` (name: the option to pick), only for a folder inside the project
    root and only while this session is not running yet (no ~/.claude/sessions file), so a transcript that quotes a
    dialog never gets a key. Each dialog on its own: Down (at most 3) until the marker is on the pick, then one Enter,
    then no key. A key goes only to a screen that changed since the last key. Done when Claude Code reports a status
    to hc or writes its session file, both of which it does only once its dialogs are passed."""
    root = os.path.realpath(cfg["_root"])
    inside = os.path.commonpath([root, os.path.realpath(s.cwd)]) == root
    seen, passed, entered = set(), set(), set()
    downs, last = dict.fromkeys(wanted, 0), [None]

    def step() -> Optional[str]:
        t = terminal(name) or {}
        if t.get("status") or live(s):
            return "up"
        if t.get("state") != "live":
            raise Fail(f"{s.name}: its terminal ended before Claude Code came up; read it: hc read {name} --lines 40")
        screen = tool("hc", "read", name, "--lines", "0")
        on = {k: dialog(screen, pick, OTHER[pick]) for k, pick in wanted.items()}
        shown = [k for k, v in on.items() if v is not None]
        passed.update(seen - set(shown))
        for k in shown:
            if not inside:
                raise Fail(f"{s.name}: Claude Code shows its {k} for {s.cwd}, which is outside the project root "
                           f"{root}; svop does not answer for it. Answer in the tab {s.tab}")
            seen.add(k)
            if k not in entered and screen != last[0] and (on[k] or downs[k] < 3) and not live(s):
                call(False, "hc", "keys", name, "enter" if on[k] else "down")
                last[0], downs[k] = screen, downs[k] + (not on[k])
                if on[k]:
                    entered.add(k)
                    print(f"{s.name}: answered \"{wanted[k]}\" ({k})")
        return None

    if poll(step):
        return
    where = f"read its screen: hc read {name}"
    if seen - passed:
        raise Fail(f"{s.name}: the {', '.join(sorted(seen - passed))} was seen but not passed in {WAIT} s; {where}")
    what = f"the {', '.join(sorted(seen))} was passed" if seen else "no first-start dialog appeared"
    print(f"{s.name}: {what}, but Claude Code did not come up in {WAIT} s; {where}", file=sys.stderr)


def space_name(cfg: Dict) -> str:
    herdr = cfg.get("herdr") or {}
    return herdr.get("space") or herdr.get("workspace") or cfg.get("project")  # `workspace`: the old spelling


def start(cfg: Dict, s: Session, view: Dict, dry: bool) -> None:
    """Run the session in its hc terminal. When the Herdr app answers, the terminal shows in the project's space
    under the session's tab label: a tab with that label is reused, else the window makes a tab and svop names it. A
    space made here comes with one tab and a shell; the first session takes the tab, then the shell is ended, so no
    empty tab is left. `view` carries what is known of the window between sessions."""
    if s.schedule:
        raise Fail(f"{s.name} runs on a schedule from launchd, not in a tab (rules/team.md, step 6)")
    name = term(cfg, s)
    running = live(s)
    if running:
        print(f"{s.name} is already live ({running}); nothing to do")
        return
    if s.sid and not transcript(s.cwd, s.sid):
        raise Fail(f"{s.name}: session_id {s.sid} has no transcript under {s.cwd}, so it cannot be resumed. "
                   f"Fix its `cwd`, or remove `session_id` from {cfg['_path']} to start it fresh")
    sid = s.sid or str(uuid.uuid4())
    if not s.sid:
        write_id(cfg, s, sid, write=not dry)
        if dry:
            print(f"# {s.name}: new session; session_id {sid} goes to {cfg['_path']}")
    if dry and cfg.get("_env_names"):
        print(f"# {s.name}: env_file {cfg['_env_file']} gives {', '.join(cfg['_env_names'])} (values not shown)")
    wanted = {}
    if not s.sid:  # a resumed session ran in its folder before
        wanted["trust dialog"] = TRUST_YES
    if s.claude.get("dangerously-load-development-channels"):
        wanted["development channels warning"] = CHANNELS_YES
    if not dry:
        t = terminal(name)
        if t and t.get("state") == "live":
            raise Fail(f"{s.name}: the hc terminal name {name} is held by a live terminal that does not run this "
                       f"session, most likely another project's session with the same terminal name (project `a`, "
                       f"session `b-c` and project `a-b`, session `c` both give `a-b-c`); read it: hc read {name}. "
                       f"Rename one of the sessions")
    space_label = space_name(cfg)
    run = ["hc", "run", "--bg", "--no-parent", "--name", name, "--cwd", s.cwd]
    space = tab = shell = None
    if dry:
        if not view.get("told"):
            view["told"] = True
            print(f"# if the Herdr app answers (herdr-app ls); with no window, hc run goes without --label and the "
                  f"herdr-app and kill lines are skipped. The first session makes the space {space_label} if missing:")
        layout = {"spaces": [{"name": space_label, "id": "<space id>"}]} if view.get("made") else {}
        if layout:
            print(f"# if the space has a tab {s.tab}, hc run gets --label herdr.tab=<its id> and no rename")
    else:
        layout = window()
        if layout is None and not view.get("told"):
            view["told"] = True
            print("svop: no Herdr window answered (herdr-app ls); the sessions run in hc only (hc ls)")
    if dry or layout is not None:
        found = find(layout, "name", space_label)
        if found is None:
            made = call(dry, "herdr-app", "do", "space.new", "--name", space_label, "--folder", cfg["_root"],
                        "--tab", s.tab)
            space, tab, shell = made.get("space", "<space id>"), made.get("tab", "<tab id>"), made.get("terminal",
                                                                                                    "<its shell>")
            view["made"] = True
        else:
            space = found["id"]
            same = [x for x in found.get("tabs", []) if x.get("name") == s.tab]
            if same and any(x.get("app") for x in same[0].get("terminals", [])):
                raise Fail(f"{s.name}: the tab {s.tab} runs another agent; close it or free it, then start again")
            tab = same[0]["id"] if same else None
        run += ["--label", f"herdr.space={space}"] + (["--label", f"herdr.tab={tab}"] if tab else [])
    address = call(dry, *run, "--", *command(cfg, s, sid, resume=bool(s.sid))).get("address")
    if not dry:
        print(f"{s.name} started in hc terminal {name}" + (f", tab {s.tab}" if space else ""))
    if space:
        shown = "<its tab id>" if dry else poll(lambda: next(
            (x["id"] for x in (find(window(), "id", space) or {}).get("tabs", [])
             if any(y.get("terminal") == address for y in x.get("terminals", []))), None))
        if shown is None:
            print(f"{s.name}: the window did not show hc terminal {name} in {WAIT} s", file=sys.stderr)
        else:
            if dry:
                print("# once the window shows it:")
            if not tab:
                call(dry, "herdr-app", "do", "tab.rename", "--id", shown, "--name", s.tab)
            if shell:
                call(dry, "hc", "kill", shell)
                call(dry, "hc", "rm", shell)
    if dry:
        for k, pick in wanted.items():
            print(f"# if Claude Code shows its {k} for {s.cwd} before it runs, only inside {cfg['_root']}: up to 3 "
                  f"Downs until \"{pick}\" is marked, then one Enter")
            print(f"# hc keys {name} down; hc keys {name} enter")
    elif wanted:
        answer(cfg, s, name, wanted)


def stop(cfg: Dict, s: Session) -> None:
    running = live(s)
    if not running:
        print(f"{s.name} is not running; nothing to do")
        return
    name = term(cfg, s)
    t = terminal(name)
    if not t or t.get("state") != "live" or running not in (t.get("foreground") or {}).get("argv", []):
        raise Fail(f"{s.name} ({running}) runs outside the hc terminal {name}; exit it there")
    status = (t.get("status") or {}).get("state")
    if status not in ("idle", "done"):
        raise Fail(f"{s.name} is {status or 'reporting no status (resumed and not used yet)'}; stop it when it is "
                   f"idle or done, or type /exit in its tab")
    call(False, "hc", "keys", name, *"/exit", "enter")  # typed, not pasted: a pasted /exit is a chat message
    print(f"{s.name}: /exit sent")


def up(cfg: Dict, dry: bool) -> int:
    failed = 0
    for repo in cfg.get("repos") or []:
        path = os.path.normpath(os.path.join(cfg["_root"], repo["path"]))
        if not os.path.exists(path):
            clone = ["gh", "repo", "clone", repo["url"], path]
            print(shlex.join(clone))
            if not dry and subprocess.run(clone).returncode != 0:
                print(f"svop: cloning {repo['url']} failed", file=sys.stderr)
                failed = 1
    view: Dict = {}
    for s in sessions(cfg):
        if s.active and not s.schedule:
            try:
                start(cfg, s, view, dry)
            except Fail as e:
                print(f"svop: {e}", file=sys.stderr)
                failed = 1
    return failed


def main(argv: List[str]) -> int:
    if argv[:1] == ["--with-env"] and argv[2:3] == ["--"]:  # inside a terminal: see command()
        try:
            env = read_env(argv[1])
        except Fail as e:
            print(f"svop: {e}", file=sys.stderr)
            return 1
        os.execvpe(argv[3], argv[3:], {**os.environ, **env})
    ap = argparse.ArgumentParser(prog="svop", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("action", choices=["up", "start", "stop"])
    ap.add_argument("project")
    ap.add_argument("session", nargs="?")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if (a.action == "up") != (a.session is None):
        ap.error("up takes a project; start and stop take a project and a session")
    try:
        cfg = load(project_dir(a.project))
        if a.action != "stop":
            check_names(cfg)
        if a.action == "up":
            return up(cfg, a.dry_run)
        s = next((x for x in sessions(cfg) if x.name == a.session), None)
        if s is None:
            raise Fail(f"no session {a.session} in {cfg['_path']}")
        start(cfg, s, {}, a.dry_run) if a.action == "start" else stop(cfg, s)
        return 0
    except Fail as e:
        print(f"svop: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
