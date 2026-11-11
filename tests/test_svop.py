"""Tests for svop.py. No test starts or stops a real session: herdr, liveness and HOME are replaced.

Run: uv run --with pyyaml python -m unittest discover tests
"""
import importlib.util
import io
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
herdr: {workspace: demo}

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
                   mock.patch.object(svop, "herdr", side_effect=self.fake_herdr),
                   mock.patch.object(svop.subprocess, "run", side_effect=AssertionError("no subprocess in tests"))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.calls = []
        self.status = "idle"
        self.cfg = svop.load(str(self.root))

    def tearDown(self):
        self.tmp.cleanup()

    def fake_herdr(self, *args):
        self.calls.append(args)
        if args[:2] == ("workspace", "list"):
            return {"result": {"workspaces": [{"label": "demo", "workspace_id": "w1"}]}}
        if args[:2] == ("workspace", "create"):
            return {"result": {"root_pane": {"pane_id": "w2:p1", "tab_id": "w2:t1", "workspace_id": "w2"},
                               "tab": {"label": "1", "tab_id": "w2:t1"}}}
        if args[:2] == ("tab", "create"):
            return {"result": {"tab": {"tab_id": "w1:t9"}, "root_pane": {"pane_id": "w1:p9"}}}
        if args[:2] == ("tab", "list"):
            return {"result": {"tabs": [{"tab_id": "w1:t5", "label": "◇ old"}, {"tab_id": "w1:t6", "label": "◇ busy"}]}}
        if args[:2] == ("pane", "list"):
            return {"result": {"panes": [{"pane_id": "w1:p3", "tab_id": "w1:t3", "agent": "claude",
                                          "agent_status": self.status, "agent_session": {"value": "live-id"}},
                                         {"pane_id": "w1:p5", "tab_id": "w1:t5", "agent": None},
                                         {"pane_id": "w1:p6", "tab_id": "w1:t6", "agent": "claude"}]}}
        return {}  # `pane run` prints nothing

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
        run = self.calls[-1]
        self.assertEqual(run[:3], ("pane", "run", "w1:p5"))  # the old tab's free shell, no new tab
        self.assertNotIn("create", [c[1] for c in self.calls])
        self.assertIn(f"claude -n old --resume {s.sid} ", run[3])

    def test_new_session_gets_an_id_written_back(self):
        s = self.session("build")
        with mock.patch.object(svop.uuid, "uuid4", return_value="22222222-2222-2222-2222-222222222222"), \
                redirect_stdout(io.StringIO()) as out:
            svop.start(self.cfg, s, {}, dry=False)
        self.assertEqual(out.getvalue(), "build started in ◇ build\n")
        self.assertIn("claude -n build --session-id 22222222-2222-2222-2222-222222222222 ", self.calls[-1][3])
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
        last = svop.shlex.split(out.getvalue().splitlines()[-1])
        self.assertEqual(last[:4], ["herdr", "pane", "run", "<pane id>"])
        self.assertEqual(svop.shlex.split(last[4])[:4], ["claude", "-n", "build", "--session-id"])

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
        self.assertNotIn("run", [c[1] for c in self.calls])

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
        line = svop.shlex.split(svop.shlex.split(out.getvalue().splitlines()[-1])[4])
        self.assertEqual(line[:4], [svop.SELF, "--with-env", str(env), "--"])
        with mock.patch.object(svop.os, "execvpe", side_effect=SystemExit) as ex, self.assertRaises(SystemExit):
            svop.main(line[1:])
        self.assertEqual(ex.call_args[0][2]["TOKEN"], "s3cr3t")
        self.assertEqual(ex.call_args[0][1][:3], ["claude", "-n", "build"])


class UpAndStop(Base):
    def test_up_starts_only_active_unscheduled(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(svop.up(self.cfg, dry=False), 0)
        runs = [c[3] for c in self.calls if c[:2] == ("pane", "run")]
        self.assertEqual([r.split()[2] for r in runs], ["demo-orchestrator", "build"])
        self.assertEqual([c for c in self.calls if c[:2] == ("workspace", "create")], [])

    def test_new_workspace_gives_its_first_pane_to_the_first_session(self):
        self.cfg["herdr"] = {"workspace": "fresh"}
        with redirect_stdout(io.StringIO()):
            svop.up(self.cfg, dry=False)
        self.assertIn(("tab", "rename", "w2:t1", "★ orchestrator"), self.calls)
        runs = [c[2] for c in self.calls if c[:2] == ("pane", "run")]
        self.assertEqual(runs, ["w2:p1", "w1:p9"])
        self.assertEqual([c[3] for c in self.calls if c[:2] == ("tab", "create")], ["w2"])

    def test_stop_types_exit_when_idle(self):
        self.status = "idle"
        with mock.patch.object(svop, "live", return_value="live-id"), redirect_stdout(io.StringIO()):
            svop.stop(self.session("build"))
        self.assertEqual(self.calls[-1], ("agent", "prompt", "w1:p3", "/exit"))

    def test_stop_refuses_when_busy(self):
        self.status = "working"
        with mock.patch.object(svop, "live", return_value="live-id"), \
                self.assertRaisesRegex(svop.Fail, "working"):
            svop.stop(self.session("build"))
        self.assertNotIn("prompt", [c[1] for c in self.calls])


if __name__ == "__main__":
    unittest.main()
