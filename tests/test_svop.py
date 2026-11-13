"""Tests for svop.py. No test starts or stops a real session: hc, herdr-app, liveness and HOME are replaced.

Run: uv run --with pyyaml python -m unittest discover tests
"""
import importlib.util
import io
import itertools
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location("svop", Path(__file__).resolve().parent.parent / "svop.py")
svop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(svop)

TEAMS = """\
# A comment that must survive.
version: 2
project: demo
herdr: {space: demo}

claude:
  permission-mode: bypassPermissions
  settings: {autoCompactEnabled: true, outputStyle: default}

orchestrator:
  session: demo-orchestrator   # the one the owner talks to
  claude:
    permission-mode: default
    allowedTools: [a, b]

teams:
  - name: build
    owns: Everything
    status: active
    claude: {append-system-prompt-file: .claude/teams/build/role.md}

  - name: old
    session_id: 11111111-1111-1111-1111-111111111111
    status: paused

  - name: daily
    status: active
    schedule: "10:07"
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.root = Path(self.tmp.name) / "demo"
        (self.root / ".claude").mkdir(parents=True)
        self.path = self.root / ".claude" / "teams.yaml"
        self.path.write_text(TEAMS)
        patches = [mock.patch.dict(os.environ, {"HOME": str(self.home)}),
                   mock.patch.object(svop, "live", return_value=None),
                   mock.patch.object(svop, "tool", side_effect=self.fake_tool),
                   mock.patch.object(svop.time, "sleep"),
                   mock.patch.object(svop.subprocess, "run", side_effect=AssertionError("no subprocess in tests"))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.calls = []
        self.terms = {}  # hc terminals by name
        self.layout = {"spaces": [{"id": "sp1", "name": "demo", "machine": None, "tabs": [
            {"id": "tb5", "name": "◇ old", "terminals": [{"terminal": "t5", "app": None}]},
            {"id": "tb6", "name": "◇ busy", "terminals": [{"terminal": "t6", "app": "claude-code"}]}]}]}
        self.screens = []
        self.cfg = svop.load(str(self.root))

    def tearDown(self):
        self.tmp.cleanup()

    def fake_tool(self, *args):
        if args[:2] == ("hc", "read"):
            return self.screens.pop(0)
        if args[0] == "hc":
            self.assertEqual(args[2], "--json")
            return svop.json.dumps(self.fake_hc(args[1], *args[3:]))
        return svop.json.dumps(self.fake_app(*args[1:]))

    def fake_hc(self, *args):
        self.calls.append(("hc",) + args)
        if args[0] == "get":
            t = self.terms.get(args[1])
            if t is None:
                raise svop.Fail('hc get: {"error":{"kind":"not_found"}}')
            # Claude Code reports a status once the scripted screens are used up: every session comes up at once
            return {**t, "status": None if self.screens else {"app": "claude-code", "state": t.get("idle", "idle")}}
        if args[0] == "run":
            name = args[args.index("--name") + 1]
            address = f"t-{name}"
            self.terms[name] = {"address": address, "state": "live"}
            labels = dict(args[i + 1].split("=", 1) for i, a in enumerate(args[:args.index("--")]) if a == "--label")
            space = next((x for x in (self.layout or {}).get("spaces", []) if x["id"] == labels.get("herdr.space")), None)
            if space is not None:
                tab = next((x for x in space["tabs"] if x["id"] == labels.get("herdr.tab")), None)
                if tab is None:
                    tab = {"id": f"tb{address}", "name": str(len(space["tabs"]) + 1), "terminals": []}
                    space["tabs"].append(tab)
                tab["terminals"].append({"terminal": address, "app": None})
            return {"address": address, "name": name, "state": "live"}
        return {}

    def fake_app(self, *args):
        self.calls.append(("herdr-app",) + args)
        if self.layout is None:
            raise svop.Fail("herdr-app ls: no window")
        if args == ("ls",):
            return self.layout
        kw = dict(zip(args[2::2], args[3::2]))
        if args[:2] == ("do", "space.new"):
            self.layout["spaces"].append({"id": "sp2", "name": kw["--name"], "machine": None, "tabs": [
                {"id": "tb1", "name": kw["--tab"], "terminals": [{"terminal": "t1", "app": None}]}]})
            return {"space": "sp2", "tab": "tb1", "terminal": "t1"}
        if args[:2] == ("do", "tab.rename"):
            for sp in self.layout["spaces"]:
                for t in sp["tabs"]:
                    if t["id"] == kw["--id"]:
                        t["name"] = kw["--name"]
            return {"ok": True}
        raise AssertionError(args)

    def runs(self):
        return [c for c in self.calls if c[:2] == ("hc", "run")]

    def run_call(self):
        return self.runs()[0]

    def tabs(self, space="demo"):
        sp = next(x for x in self.layout["spaces"] if x["name"] == space)
        return {t["name"]: [x["terminal"] for x in t["terminals"]] for t in sp["tabs"]}

    def session(self, name):
        return self.session_of(self.cfg, name)

    @staticmethod
    def session_of(cfg, name):
        return next(s for s in svop.sessions(cfg) if s.name == name)

    def transcript_for(self, s, sid):
        folder = self.home / ".claude" / "projects" / svop.re.sub(r"[^a-zA-Z0-9]", "-", os.path.realpath(s.cwd))
        folder.mkdir(parents=True)
        (folder / f"{sid}.jsonl").write_text("{}\n")


class Flags(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(svop.flags({"model": "opus", "verbose": True, "debug": False, "allowedTools": ["a", "b"],
                                     "settings": {"autoCompactEnabled": True, "outputStyle": "default"},
                                     "effort": "medium"}),
                         ["--model", "opus", "--verbose", "--allowedTools", "a", "b",
                          "--settings", '{"autoCompactEnabled":true,"outputStyle":"default"}', "--effort", "medium"])

    def test_home_path(self):
        with mock.patch.dict(os.environ, {"HOME": "/h"}):
            self.assertEqual(svop.flags({"mcp-config": "~/x.json"}), ["--mcp-config", "/h/x.json"])


class Merge(Base):
    def test_session_over_project_key_by_key(self):
        orch = self.session("demo-orchestrator")
        self.assertEqual(orch.claude, {"permission-mode": "default", "allowedTools": ["a", "b"],
                                       "settings": {"autoCompactEnabled": True, "outputStyle": "default"}})
        build = self.session("build")
        self.assertEqual(build.claude["permission-mode"], "bypassPermissions")
        self.assertEqual(build.claude["append-system-prompt-file"], ".claude/teams/build/role.md")

    def test_derived_names(self):
        self.assertEqual(self.session("demo-orchestrator").tab, "★ orchestrator")
        self.assertEqual(self.session("build").tab, "◇ build")
        self.assertEqual(self.session("build").cwd, str(self.root))

    def test_version_1_is_refused(self):
        self.path.write_text("version: 1\nproject: demo\n")
        with self.assertRaisesRegex(svop.Fail, "not version 2"):
            svop.load(str(self.root))


class Resume(Base):
    def test_missing_transcript_is_an_error(self):
        s = self.session("old")
        with self.assertRaisesRegex(svop.Fail, "cannot be resumed"):
            svop.start(self.cfg, s, {}, dry=False)
        self.assertEqual(self.calls, [])

    def test_existing_transcript_resumes(self):
        s = self.session("old")
        self.transcript_for(s, s.sid)
        with redirect_stdout(io.StringIO()):
            svop.start(self.cfg, s, {}, dry=False)
        run = self.run_call()
        self.assertEqual(run[:8], ("hc", "run", "--bg", "--no-parent", "--name", "demo-old", "--cwd", str(self.root)))
        self.assertIn("herdr.tab=tb5", run)  # the old tab, no new one
        self.assertEqual(run[run.index("--") + 1:][:4], ("claude", "-n", "old", "--resume"))
        self.assertEqual([c for c in self.calls if c[0] == "herdr-app" and c[1] == "do"], [])
        self.assertEqual(self.tabs()["◇ old"], ["t5", "t-demo-old"])

    def test_new_session_gets_an_id_written_back(self):
        s = self.session("build")
        with mock.patch.object(svop.uuid, "uuid4", return_value="22222222-2222-2222-2222-222222222222"), \
                redirect_stdout(io.StringIO()) as out:
            svop.start(self.cfg, s, {}, dry=False)
        self.assertEqual(out.getvalue(), "build started in hc terminal demo-build, tab ◇ build\n")
        run = self.run_call()
        self.assertEqual(run[run.index("--") + 1:][:5],
                         ("claude", "-n", "build", "--session-id", "22222222-2222-2222-2222-222222222222"))
        self.assertIn("herdr.space=sp1", run)
        self.assertNotIn("herdr.tab", " ".join(run))
        self.assertIn(("herdr-app", "do", "tab.rename", "--id", "tbt-demo-build", "--name", "◇ build"), self.calls)
        self.assertEqual(self.tabs()["◇ build"], ["t-demo-build"])
        text = self.path.read_text()
        self.assertEqual(text, TEAMS.replace("  - name: build\n",
                                             "  - name: build\n    session_id: 22222222-2222-2222-2222-222222222222\n"))

    def test_orchestrator_id_written_under_session(self):
        cfg = svop.load(str(self.root))
        svop.write_id(cfg, self.session("demo-orchestrator"), "abc", write=True)
        self.assertIn("  session: demo-orchestrator   # the one the owner talks to\n  session_id: abc\n",
                      self.path.read_text())
        self.assertEqual(svop.load(str(self.root))["orchestrator"]["session_id"], "abc")

    def test_dry_run_writes_and_runs_nothing(self):
        out = io.StringIO()
        with redirect_stdout(out):
            svop.start(self.cfg, self.session("build"), {}, dry=True)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.path.read_text(), TEAMS)
        self.assertIn("herdr-app do space.new --name demo", out.getvalue())
        run = svop.shlex.split(next(x for x in out.getvalue().splitlines() if x.startswith("hc run")))
        self.assertEqual(run[:6], ["hc", "run", "--bg", "--no-parent", "--name", "demo-build"])
        self.assertEqual(run[run.index("--") + 1:][:4], ["claude", "-n", "build", "--session-id"])
        for shown in ("hc kill '<its shell>'", "hc rm '<its shell>'", "hc keys demo-build down"):
            self.assertIn(shown, out.getvalue())

    def test_write_happens_before_start_and_flow_form_is_refused(self):
        self.path.write_text(TEAMS.replace("orchestrator:\n  session: demo-orchestrator   # the one the owner talks to\n",
                                           "orchestrator: {session: demo-orchestrator}\n"
                                           "orchestrator_notes:\n  session: elsewhere\n").replace(
            "  claude:\n    permission-mode: default\n    allowedTools: [a, b]\n", ""))
        cfg = svop.load(str(self.root))
        before = self.path.read_text()
        with self.assertRaisesRegex(svop.Fail, "block form"):
            svop.start(cfg, self.session_of(cfg, "demo-orchestrator"), {}, dry=False)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.path.read_text(), before)

    def test_write_stays_in_the_orchestrator_block(self):
        self.path.write_text(TEAMS.replace("  session: demo-orchestrator   # the one the owner talks to\n", "  herdr: {tab: x}\n"
                                           ).replace("orchestrator:\n", "orchestrator:\n  session: demo-orchestrator\n", 1
                                           ).replace("teams:\n", "other:\n  session: not-here\nteams:\n"))
        cfg = svop.load(str(self.root))
        svop.write_id(cfg, self.session_of(cfg, "demo-orchestrator"), "abc", write=True)
        self.assertIn("orchestrator:\n  session: demo-orchestrator\n  session_id: abc\n", self.path.read_text())

    def test_tab_with_the_label_running_another_agent_is_refused(self):
        with self.assertRaisesRegex(svop.Fail, "runs another agent"):
            svop.start(self.cfg, self.session("build")._replace(tab="◇ busy"), {}, dry=False)
        self.assertEqual(self.runs(), [])

    def test_name_hc_cannot_hold_is_refused(self):
        with self.assertRaisesRegex(svop.Fail, "demo-Build must be 1-32 of a-z"):
            svop.start(self.cfg, self.session("build")._replace(name="Build"), {}, dry=True)
        with self.assertRaisesRegex(svop.Fail, "1-32 of a-z"):
            svop.start(self.cfg, self.session("build")._replace(name="b" * 28), {}, dry=True)
        self.assertEqual(self.path.read_text(), TEAMS)

    def test_every_name_is_checked_before_anything_starts(self):
        self.path.write_text(TEAMS.replace("  - name: old\n", "  - name: Old\n"))
        with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(svop.main(["up", str(self.root)]), 1)
        self.assertIn("demo-Old must be 1-32", err.getvalue())
        self.assertEqual(self.calls, [])
        self.assertNotIn("session_id", self.path.read_text().split("name: build")[1].split("name:")[0])

    def test_two_sessions_with_one_terminal_name_are_refused(self):
        self.path.write_text(TEAMS.replace("  - name: old\n", "  - name: demo-build\n"))
        with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(svop.main(["start", str(self.root), "demo-orchestrator"]), 1)
        self.assertIn("build and demo-build both give the hc terminal name demo-build", err.getvalue())
        self.assertEqual(self.calls, [])

    def test_terminal_name_is_project_and_session_once(self):
        self.assertEqual(svop.term(self.cfg, self.session("build")), "demo-build")
        self.assertEqual(svop.term(self.cfg, self.session("demo-orchestrator")), "demo-orchestrator")

    def test_live_terminal_of_the_name_is_refused(self):
        self.terms["demo-build"] = {"address": "t3", "state": "live"}
        with self.assertRaisesRegex(svop.Fail, "held by a live terminal that does not run this session, most likely another project"):
            svop.start(self.cfg, self.session("build"), {}, dry=False)
        self.assertEqual(self.runs(), [])

    def test_old_workspace_spelling_names_the_space(self):
        self.path.write_text(TEAMS.replace("herdr: {space: demo}", "herdr: {workspace: demo}"))
        self.assertEqual(svop.space_name(svop.load(str(self.root))), "demo")

    def test_live_session_is_left_alone(self):
        with mock.patch.object(svop, "live", return_value="live-id"), redirect_stdout(io.StringIO()) as out:
            svop.start(self.cfg, self.session("build"), {}, dry=False)
        self.assertEqual(self.calls, [])
        self.assertIn("already live", out.getvalue())

    def test_scheduled_team_is_refused(self):
        with self.assertRaisesRegex(svop.Fail, "launchd"):
            svop.start(self.cfg, self.session("daily"), {}, dry=False)


class Env(Base):
    def write_env(self, text):
        env = self.root / "x.env"
        env.write_text(text)
        self.path.write_text(TEAMS.replace("project: demo\n", f"project: demo\nenv_file: {env}\n"))
        return env

    def test_parsed_as_data(self):
        env = self.write_env("# c\n\nA=1\nB='two words'\nC=\"$(x)\"\n")
        self.assertEqual(svop.read_env(str(env)), {"A": "1", "B": "two words", "C": "$(x)"})

    def test_bad_line_and_missing_file_fail_before_start(self):
        self.write_env("A=1\nexport SECRET value\n")
        with self.assertRaisesRegex(svop.Fail, "line 2"):
            svop.load(str(self.root))
        (self.root / "x.env").unlink()
        with self.assertRaisesRegex(svop.Fail, "cannot be read"):
            svop.load(str(self.root))

    def test_values_reach_only_claude_and_are_never_printed(self):
        env = self.write_env("TOKEN=s3cr3t\n")
        cfg = svop.load(str(self.root))
        out = io.StringIO()
        with redirect_stdout(out):
            svop.start(cfg, self.session_of(cfg, "build"), {}, dry=True)
        self.assertNotIn("s3cr3t", out.getvalue())
        self.assertIn("TOKEN", out.getvalue())
        run = svop.shlex.split(next(x for x in out.getvalue().splitlines() if x.startswith("hc run")))
        line = run[run.index("--") + 1:]
        self.assertEqual(line[:4], [svop.SELF, "--with-env", str(env), "--"])
        with mock.patch.object(svop.os, "execvpe", side_effect=SystemExit) as ex, self.assertRaises(SystemExit):
            svop.main(line[1:])
        self.assertEqual(ex.call_args[0][2]["TOKEN"], "s3cr3t")
        self.assertEqual(ex.call_args[0][1][:3], ["claude", "-n", "build"])


DIALOG = """ Accessing workspace:
 /some/folder
 Quick safety check: Is this a project you created or one you trust?
 {no} No, exit
 {yes} Yes, I trust this folder
 Enter to confirm · Esc to cancel
"""
ON_NO, ON_YES = DIALOG.format(no="❯", yes=" "), DIALOG.format(no=" ", yes="❯")
CHANNELS = """  WARNING: Loading development channels
  ❯ 1. I am using this for local development
    2. Exit
  Enter to confirm · Esc to cancel
"""
CHAT = """❯ Write "No, exit", then "Yes, I trust this folder", then "Enter to confirm".
⏺ No, exit / ❯ Yes, I trust this folder / Enter to confirm
"""


class Trust(Base):
    def keys(self):
        return [c[3] for c in self.calls if c[:2] == ("hc", "keys")]

    def start(self, s=None, ticks=None):
        clock = mock.patch.object(svop.time, "monotonic", side_effect=[0, 0] + ticks if ticks else itertools.count())
        with clock, redirect_stdout(io.StringIO()) as out, mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            try:
                svop.start(self.cfg, s or self.session("build"), {}, dry=False)
            finally:
                self.out, self.err = out.getvalue(), err.getvalue()

    def test_dialog_is_answered_yes(self):
        self.screens = ["", ON_NO, ON_YES, ""]
        self.start()
        self.assertEqual(self.keys(), ["down", "enter"])
        self.assertIn('build: answered "Yes, I trust this folder" (trust dialog)', self.out)

    def test_stale_screen_gets_no_second_key(self):
        self.screens = [ON_NO, ON_NO, ON_YES, ON_YES, ON_YES, ""]
        self.start()
        self.assertEqual(self.keys(), ["down", "enter"])

    def test_nothing_after_enter(self):
        self.screens = [ON_YES, ON_NO, ON_NO + " ", ""]
        self.start()
        self.assertEqual(self.keys(), ["enter"])

    def test_at_most_three_downs(self):
        self.screens = [ON_NO + " " * i for i in range(5)]
        with self.assertRaisesRegex(svop.Fail, "seen but not passed"):
            self.start(ticks=[0, 1, 2, 3, 4, 5, 99])
        self.assertEqual(self.keys(), ["down"] * 3)

    def test_chat_text_gets_no_key(self):
        self.screens = [CHAT, CHAT]
        self.start()
        self.assertEqual(self.keys(), [])

    def test_resumed_session_is_never_answered(self):
        s = self.session("old")
        self.transcript_for(s, s.sid)
        self.screens = [ON_YES]
        self.start(s)
        self.assertEqual(self.keys(), [])
        self.assertNotIn(("hc", "get", "demo-old"), self.calls[1:])  # one get before the start, none after

    def test_timeout_without_a_dialog(self):
        self.screens = [ON_YES.replace("Enter to confirm", "")] * 3
        self.start(ticks=[0, 1, 2, 3, 99])
        self.assertEqual(self.keys(), [])
        self.assertIn("no first-start dialog appeared", self.err)

    def test_timeout_after_the_dialog_passed(self):
        self.screens = [ON_YES, "", ""]
        self.start(ticks=[0, 1, 2, 3, 99])
        self.assertEqual(self.keys(), ["enter"])
        self.assertIn("the trust dialog was passed, but Claude Code did not come up", self.err)

    def test_dialog_seen_but_not_passed_exits_non_zero(self):
        self.screens = [ON_NO, ON_YES, ON_YES]
        with mock.patch.object(svop.time, "monotonic", side_effect=[0, 0, 0, 1, 2, 3, 99]), \
                redirect_stdout(io.StringIO()), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(svop.main(["start", str(self.root), "build"]), 1)
        self.assertEqual(self.keys(), ["down", "enter"])
        self.assertIn("seen but not passed", err.getvalue())

    def test_folder_outside_the_project_is_never_answered(self):
        self.screens = [ON_YES]
        with self.assertRaisesRegex(svop.Fail, "outside the project root"):
            self.start(self.session("build")._replace(cwd=str(self.root.parent / "elsewhere")))
        self.assertEqual(self.keys(), [])

    def test_dry_run_says_it_and_sends_nothing(self):
        with redirect_stdout(io.StringIO()) as out:
            svop.start(self.cfg, self.session("build"), {}, dry=True)
        self.assertIn("trust dialog", out.getvalue())
        self.assertEqual(self.calls, [])

    def test_channels_warning_is_answered_even_on_resume(self):
        s = self.session("old")._replace(claude={"dangerously-load-development-channels": "server:x"})
        self.transcript_for(s, s.sid)
        self.screens = [ON_YES, CHANNELS, ""]  # the trust dialog of a resumed session gets no key
        self.start(s)
        self.assertEqual(self.keys(), ["enter"])
        self.assertIn('old: answered "I am using this for local development"', self.out)

    def test_both_dialogs_in_turn(self):
        s = self.session("build")._replace(claude={"dangerously-load-development-channels": "server:x"})
        self.screens = [ON_NO, ON_YES, CHANNELS, CHANNELS, ""]
        self.start(s)
        self.assertEqual(self.keys(), ["down", "enter", "enter"])

    def test_a_running_session_never_gets_a_key(self):
        # its transcript may quote a dialog; a running session has its ~/.claude/sessions file
        s = self.session("old")._replace(claude={"dangerously-load-development-channels": "server:x"})
        self.transcript_for(s, s.sid)
        self.screens = [CHANNELS]
        with mock.patch.object(svop, "live", side_effect=[None, None, "live-id"]):
            self.start(s)
        self.assertEqual(self.keys(), [])
        self.assertEqual(self.err, "")

    def test_resumed_session_that_reports_no_status_ends_the_wait_quietly(self):
        s = self.session("old")._replace(claude={"dangerously-load-development-channels": "server:x"})
        self.transcript_for(s, s.sid)
        self.screens = [CHANNELS, CHANNELS + " ", CHANNELS + "  "]  # the status never comes
        with mock.patch.object(svop, "live", side_effect=[None, None, None, "live-id"]):
            self.start(s)
        self.assertEqual(self.keys(), ["enter"])
        self.assertEqual(self.err, "")

    def test_a_second_marker_is_not_the_dialog(self):
        self.assertIsNone(svop.dialog(CHANNELS + "❯ \n", svop.CHANNELS_YES, "Exit"))

    def test_ended_terminal_stops_the_wait(self):
        self.screens = [ON_NO]
        with mock.patch.object(svop, "terminal", side_effect=[None, {"state": "finished"}]), \
                self.assertRaisesRegex(svop.Fail, "ended before Claude Code came up"):
            self.start()


class UpAndStop(Base):
    def test_up_starts_only_active_unscheduled(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(svop.up(self.cfg, dry=False), 0)
        self.assertEqual([r[5] for r in self.runs()], ["demo-orchestrator", "demo-build"])
        self.assertNotIn("space.new", [c[2] for c in self.calls if c[0] == "herdr-app" and len(c) > 2])
        self.assertEqual(self.tabs()["★ orchestrator"], ["t-demo-orchestrator"])
        self.assertEqual(self.tabs()["◇ build"], ["t-demo-build"])

    def test_new_space_gives_its_first_tab_to_the_first_session(self):
        self.cfg["herdr"] = {"space": "fresh"}
        with redirect_stdout(io.StringIO()):
            svop.up(self.cfg, dry=False)
        self.assertIn(("herdr-app", "do", "space.new", "--name", "fresh", "--folder", str(self.root),
                       "--tab", "★ orchestrator"), self.calls)
        self.assertIn("herdr.tab=tb1", self.runs()[0])
        self.assertIn(("hc", "kill", "t1"), self.calls)  # the space's own shell, once the session shows
        self.assertIn(("hc", "rm", "t1"), self.calls)
        self.assertEqual(self.tabs("fresh"), {"★ orchestrator": ["t1", "t-demo-orchestrator"], "◇ build": ["t-demo-build"]})

    def test_dry_up_shows_every_command_and_runs_nothing(self):
        with redirect_stdout(io.StringIO()) as out:
            svop.up(self.cfg, dry=True)
        self.assertEqual(self.calls, [])
        lines = [x for x in out.getvalue().splitlines() if not x.startswith("#")]
        self.assertEqual([x.split()[:3] for x in lines], [
            ["herdr-app", "do", "space.new"], ["hc", "run", "--bg"], ["hc", "kill", "'<its"], ["hc", "rm", "'<its"],
            ["hc", "run", "--bg"], ["herdr-app", "do", "tab.rename"]])

    def test_no_window_starts_all_and_says_it_once(self):
        self.layout = None
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(svop.up(self.cfg, dry=False), 0)
        self.assertEqual([r[5] for r in self.runs()], ["demo-orchestrator", "demo-build"])
        self.assertNotIn("--label", sum(self.runs(), ()))
        self.assertEqual(out.getvalue().count("no Herdr window answered"), 1)

    def stop(self, status, argv=("claude", "--resume", "live-id")):
        self.terms["demo-build"] = {"address": "t3", "state": "live", "idle": status,
                                    "foreground": {"argv": list(argv)}}
        with mock.patch.object(svop, "live", return_value="live-id"), redirect_stdout(io.StringIO()):
            svop.stop(self.cfg, self.session("build"))

    def test_stop_types_exit_when_idle_or_done(self):
        for status in ("idle", "done"):
            self.stop(status)
            self.assertEqual(self.calls[-1], ("hc", "keys", "demo-build", "/", "e", "x", "i", "t", "enter"))

    def test_stop_refuses_when_busy(self):
        with self.assertRaisesRegex(svop.Fail, "working"):
            self.stop("working")
        self.assertNotIn("keys", [c[1] for c in self.calls])

    def test_stop_refuses_a_terminal_running_another_session(self):
        with self.assertRaisesRegex(svop.Fail, "runs outside the hc terminal demo-build"):
            self.stop("idle", argv=("claude", "--resume", "other-id"))
        self.assertNotIn("keys", [c[1] for c in self.calls])


if __name__ == "__main__":
    unittest.main()
