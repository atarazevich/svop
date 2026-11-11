#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Start and stop a project's Claude Code sessions in herdr, as `.claude/teams.yaml` (version 2) says.

Usage:
  svop up <project> [--dry-run]              clone missing repos, make sure the herdr workspace exists,
                                             start every active session that has no schedule
  svop start <project> <session> [--dry-run] start one session; a live one is left alone
  svop stop <project> <session>              type /exit into the session's pane, only when it is idle

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
import uuid
from typing import Dict, List, NamedTuple, Optional

import yaml

REGISTRY = "~/.cache/router/projects.json"
SELF = os.path.realpath(__file__)


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
    # pane's shell, its history, or a command line.
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


def herdr(*args: str) -> Dict:
    out = subprocess.run(["herdr", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise Fail(f"herdr {' '.join(args)}: {out.stderr.strip() or out.stdout.strip()}")
    return json.loads(out.stdout) if out.stdout.strip() else {}  # `pane run` prints nothing


def pane_for(cfg: Dict, s: Session, ws: Dict, dry: bool) -> str:
    """The pane the session runs in. A tab with the session's label whose pane runs no agent (a shell left by an
    ended session) is reused; else a new tab. A workspace created here comes with one tab and pane; the first
    session takes it, so no empty tab is left. `ws` carries the workspace id between sessions."""
    label = (cfg.get("herdr") or {}).get("workspace") or cfg.get("project")
    create = ["herdr", "workspace", "create", "--label", label, "--cwd", s.cwd, "--no-focus"]
    tab = ["herdr", "tab", "create", "--workspace", ws.get("id", "<workspace id>"), "--cwd", s.cwd,
           "--label", s.tab, "--no-focus"]
    if dry:
        if "id" not in ws:
            ws["id"] = "<workspace id>"
            print(f"# if no workspace is labelled {label}:")
            print(shlex.join(create))
            print(shlex.join(["herdr", "tab", "rename", "<tab id>", s.tab]))
            print("# else:")
        print(f"# if a tab labelled {s.tab} has a pane with no agent, the command runs there; else:")
        print(shlex.join(tab))
        return "<pane id>"
    if "id" not in ws:
        found = [w["workspace_id"] for w in herdr("workspace", "list")["result"]["workspaces"] if w.get("label") == label]
        if found:
            ws["id"] = tab[4] = found[0]
        else:
            made = herdr(*create[1:])["result"]
            ws["id"] = made["root_pane"]["workspace_id"]
            herdr("tab", "rename", made["tab"]["tab_id"], s.tab)
            return made["root_pane"]["pane_id"]
    tabs = {t["tab_id"] for t in herdr("tab", "list", "--workspace", ws["id"])["result"]["tabs"] if t.get("label") == s.tab}
    if tabs:
        panes = herdr("pane", "list", "--workspace", ws["id"])["result"]["panes"]
        free = [p["pane_id"] for p in panes if p.get("tab_id") in tabs and not p.get("agent")]
        if not free:
            raise Fail(f"{s.name}: the tab {s.tab} runs another agent; close it or free it, then start again")
        return free[0]
    return herdr(*tab[1:])["result"]["root_pane"]["pane_id"]


def start(cfg: Dict, s: Session, ws: Dict, dry: bool) -> None:
    if s.schedule:
        raise Fail(f"{s.name} runs on a schedule from launchd, not in a tab (rules/team.md, step 6)")
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
    pane = pane_for(cfg, s, ws, dry)
    run = ["herdr", "pane", "run", pane, shlex.join(command(cfg, s, sid, resume=bool(s.sid)))]
    if dry:
        print(shlex.join(run))
        return
    herdr(*run[1:])
    print(f"{s.name} started in {s.tab}")


def stop(s: Session) -> None:
    running = live(s)
    if not running:
        print(f"{s.name} is not running; nothing to do")
        return
    panes = herdr("pane", "list")["result"]["panes"]
    pane = next((p for p in panes if (p.get("agent_session") or {}).get("value") == running), None)
    if pane is None:
        raise Fail(f"{s.name} ({running}) runs outside herdr; exit it there")
    if pane.get("agent_status") not in ("idle", "done"):
        raise Fail(f"{s.name} is {pane.get('agent_status')}; stop it when it is idle")
    herdr("agent", "prompt", pane["pane_id"], "/exit")
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
    ws: Dict = {}
    for s in sessions(cfg):
        if s.active and not s.schedule:
            try:
                start(cfg, s, ws, dry)
            except Fail as e:
                print(f"svop: {e}", file=sys.stderr)
                failed = 1
    return failed


def main(argv: List[str]) -> int:
    if argv[:1] == ["--with-env"] and argv[2:3] == ["--"]:  # inside a pane: see command()
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
        if a.action == "up":
            return up(cfg, a.dry_run)
        s = next((x for x in sessions(cfg) if x.name == a.session), None)
        if s is None:
            raise Fail(f"no session {a.session} in {cfg['_path']}")
        start(cfg, s, {}, a.dry_run) if a.action == "start" else stop(s)
        return 0
    except Fail as e:
        print(f"svop: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
