"""Tests for dashboard/issues.py with invented projects. No network: gh is replaced; git runs on temp repos."""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "issues", Path(__file__).resolve().parent.parent / "dashboard" / "issues.py")
issues = importlib.util.module_from_spec(spec)
spec.loader.exec_module(issues)
Issue, Project = issues.Issue, issues.Project


def t(*args):
    return datetime(*args, tzinfo=timezone.utc)


def git(repo, *args, when=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
    if when:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


def commit_file(repo, rel, text, when):
    path = Path(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "x", when=when)


def make_repo(path):
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    return path


class IssueFiles(unittest.TestCase):
    def test_created_closed_reopened_and_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp) / "garden")
            fm = "---\nstatus: {}\n---\n# Water the ferns\n"
            commit_file(repo, "docs/issues/ferns.md", fm.format("idea"), "2026-03-02T10:00:00Z")
            commit_file(repo, "docs/issues/pots.md", fm.format("ready"), "2026-03-03T10:00:00Z")
            commit_file(repo, "docs/issues/ferns.md", fm.format("done"), "2026-03-09T10:00:00Z")
            commit_file(repo, "docs/issues/ferns.md", fm.format("ready"), "2026-03-10T10:00:00Z")
            commit_file(repo, "docs/issues/ferns.md", fm.format("done"), "2026-03-12T10:00:00Z")
            (repo / "docs/issues/pots.md").unlink()
            git(repo, "add", "-A")
            git(repo, "commit", "-m", "x", when="2026-03-20T10:00:00Z")
            commit_file(repo, "docs/issues/soil.md", "# no frontmatter\n", "2026-03-21T10:00:00Z")
            commit_file(repo, "notes.md", "status: done\n", "2026-03-22T10:00:00Z")
            got = issues.file_issues(repo)
        self.assertEqual(got, [
            Issue(t(2026, 3, 2, 10), t(2026, 3, 12, 10), 1),
            Issue(t(2026, 3, 3, 10), t(2026, 3, 20, 10), 0),
            Issue(t(2026, 3, 21, 10), None, 0),
        ])

    def test_rename_keeps_the_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp) / "garden")
            body = "---\nstatus: {}\n---\n# Build a trellis\n" + "".join(f"step {k}\n" for k in range(20))
            commit_file(repo, "docs/issues/trellis.md", body.format("ready"), "2026-03-02T10:00:00Z")
            git(repo, "mv", "docs/issues/trellis.md", "docs/issues/07-trellis.md")
            git(repo, "commit", "-m", "x", when="2026-03-04T10:00:00Z")
            git(repo, "mv", "docs/issues/07-trellis.md", "docs/issues/7-trellis.md")
            (repo / "docs/issues/7-trellis.md").write_text(body.format("done"))
            git(repo, "add", "-A")
            git(repo, "commit", "-m", "x", when="2026-03-06T10:00:00Z")
            got = issues.file_issues(repo)
        self.assertEqual(got, [Issue(t(2026, 3, 2, 10), t(2026, 3, 6, 10), 0)])

    def test_added_already_done_counts_as_closed_without_a_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp) / "garden")
            commit_file(repo, "docs/issues/old.md", "---\nstatus: done\n---\n", "2026-03-02T10:00:00Z")
            commit_file(repo, "docs/issues/new.md", "---\nstatus: idea\n---\n", "2026-03-02T10:00:00Z")
            commit_file(repo, "docs/issues/new.md", "---\nstatus: done\n---\n", "2026-03-03T10:00:00Z")
            got = issues.file_issues(repo)
        self.assertEqual(got, [Issue(t(2026, 3, 2, 10), t(2026, 3, 2, 10), 0, False),
                               Issue(t(2026, 3, 2, 10), t(2026, 3, 3, 10), 0, True)])
        self.assertEqual(issues.median_days(got), 1.0)
        page = issues.render([Project("garden", got)], "t")
        self.assertIn("1 without a start date", page)
        self.assertIn("<b>2</b><span>closed</span>", page)

    def test_status_counts_only_inside_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp) / "garden")
            text = "---\nstatus: ready\n---\n# Fence\n\nstatus: done\n"
            commit_file(repo, "docs/issues/fence.md", text, "2026-03-02T10:00:00Z")
            commit_file(repo, "docs/issues/fence.md", text + "status: done again\n", "2026-03-05T10:00:00Z")
            got = issues.file_issues(repo)
        self.assertEqual(got, [Issue(t(2026, 3, 2, 10), None, 0)])
        self.assertIsNone(issues.frontmatter_status(["# Title", "status: done"]))
        self.assertEqual(issues.frontmatter_status(["---", "title: x", "Status: 'Done'", "---"]), "done")

    def test_author_date_not_committer_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp) / "garden")
            commit_file(repo, "docs/issues/a.md", "---\nstatus: idea\n---\n", "2026-03-02T10:00:00Z")
            git(repo, "commit", "--amend", "-q", "--no-edit", "--no-reset-author", when=None)
            got = issues.file_issues(repo)
        self.assertEqual(got[0].created, t(2026, 3, 2, 10))


class Finding(unittest.TestCase):
    def test_symlinks_nested_repos_worktrees_and_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, elsewhere = Path(tmp) / "root", Path(tmp) / "elsewhere"
            root.mkdir()
            commit_file(make_repo(root / "alpha"), "a.txt", "a", "2026-01-01T00:00:00Z")
            git(root / "alpha", "worktree", "add", "-q", str(root / "alpha-wt"), "-b", "wt")
            make_repo(elsewhere / "beta")
            os.symlink(elsewhere / "beta", root / "beta")
            make_repo(root / "group" / "one")
            make_repo(root / "group" / "two")
            (root / "plain").mkdir()
            (root / ".hidden").mkdir()
            projects, skipped = issues.find_repos(root)
        self.assertEqual(sorted(projects), ["alpha", "beta", "group"])
        self.assertEqual([p.name for p in projects["group"]], ["one", "two"])
        self.assertEqual(dict(skipped), {
            "plain": "not a git repository",
            "alpha-wt": "worktree or second checkout of another project's repository"})


class GitHub(unittest.TestCase):
    def test_issues_and_reopens_from_gh(self):
        listed = json.dumps([
            {"number": 2, "title": "Paint the shed", "state": "OPEN", "createdAt": "2026-04-06T23:30:00Z",
             "closedAt": None, "labels": [], "milestone": None},
            {"number": 1, "title": "Fix the gate", "state": "CLOSED", "createdAt": "2026-04-01T08:00:00Z",
             "closedAt": "2026-04-05T09:00:00Z", "labels": [], "milestone": None},
        ])
        calls = []

        def runner(cmd, cwd):
            calls.append(cmd)
            if cmd[:3] == ["git", "remote", "get-url"]:
                return "git@github.com:someone/garden.git\n"
            if cmd[:2] == ["git", "remote"]:
                return "upstream\norigin\n"
            if cmd[:3] == ["gh", "issue", "list"]:
                return listed
            if cmd[:2] == ["gh", "api"]:  # page 1 full (100 events), page 2 short
                return "100\n1\n7\n" if cmd[2].endswith("page=1") else "40\n1\n"
            return None

        self.assertEqual(issues.github_slug(Path("."), runner), "someone/garden")
        self.assertEqual(calls[1], ["git", "remote", "get-url", "origin"])
        self.assertEqual(issues.gh_issues("someone/garden", runner), ([
            Issue(t(2026, 4, 1, 8), t(2026, 4, 5, 9), 2), Issue(t(2026, 4, 6, 23, 30), None, 0)], []))
        self.assertEqual(sum(c[:2] == ["gh", "api"] for c in calls), 2)
        self.assertEqual(issues.gh_issues("someone/garden", lambda cmd, cwd: None, lambda cmd: "why"),
                         (None, ["why"]))

    def test_notes_on_cut_offs_and_failed_pages(self):
        row = {"number": 1, "createdAt": "2026-04-01T08:00:00Z", "closedAt": None}
        full = json.dumps([dict(row, number=n) for n in range(1, issues.MAX_ISSUES + 1)])

        def runner(cmd, cwd):
            if cmd[1] == "issue":
                return full
            return "100\n" if cmd[2].endswith("page=1") else None

        got, notes = issues.gh_issues("someone/garden", runner, lambda cmd: "unused")
        self.assertEqual(len(got), issues.MAX_ISSUES)
        self.assertEqual(notes, [f"first {issues.MAX_ISSUES} issues only", "reopens incomplete (gh failed on page 2)"])

    def test_reopen_paging_stops_after_max_pages(self):
        pages = []

        def runner(cmd, cwd):
            pages.append(cmd)
            return "100\n3\n"

        counts, cut = issues.reopens("someone/garden", runner)
        self.assertEqual((counts, len(pages)), ({3: issues.MAX_PAGES}, issues.MAX_PAGES))
        self.assertIn("stopped after", cut)


class Ownership(unittest.TestCase):
    def test_someone_elses_clone_is_skipped_and_never_asked_about(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remotes = {"mine": "git@github.com:me/mine.git", "team": "https://github.com/MyOrg/team",
                       "upstream": "https://github.com/stranger/upstream.git"}
            for name, url in remotes.items():
                commit_file(make_repo(root / name), "docs/issues/a.md", "---\nstatus: idea\n---\n",
                            "2026-05-04T10:00:00Z")
                git(root / name, "remote", "add", "origin", url)
            commit_file(make_repo(root / "local"), "docs/issues/b.md", "---\nstatus: idea\n---\n",
                        "2026-05-05T10:00:00Z")
            asked = []

            def runner(cmd, cwd):
                if cmd[0] == "gh":
                    asked.append(cmd[4] if cmd[1] == "issue" else cmd[2])
                    return "[]" if cmd[1] == "issue" else "0\n"
                return issues.run(cmd, cwd)

            allowed = issues.owners("me", lambda cmd, cwd: "MyOrg\n")
            projects, skipped = issues.gather(root, allowed, runner)
        self.assertEqual(allowed, {"me", "myorg"})
        self.assertEqual([p.name for p in projects], ["local", "mine", "team"])
        self.assertEqual(skipped, [("upstream", "not the owner's repository")])
        self.assertFalse([a for a in asked if "stranger" in a])
        self.assertIn("me/mine", asked)


PROJECTS = [
    Project("orchard", [Issue(t(2026, 1, 5), t(2026, 1, 9, 12), 0), Issue(t(2026, 2, 2), None, 1)]),
    Project("kiln", [Issue(t(2026, 1, 20), t(2026, 3, 3), 0)]),
]


class Numbers(unittest.TestCase):
    def test_axis_and_counts(self):
        axis = issues.weeks(PROJECTS)
        self.assertEqual((axis[0], axis[-1], len(axis)), (date(2026, 1, 5), date(2026, 3, 2), 9))
        every = [i for p in PROJECTS for i in p.issues]
        self.assertEqual(issues.per_week([i.created for i in every], axis), [1, 0, 1, 0, 1, 0, 0, 0, 0])
        self.assertEqual(issues.open_at_week_end(every, axis), [0, 0, 1, 1, 2, 2, 2, 2, 1])
        self.assertEqual(issues.fmt_days(issues.median_days(every)), "23 d")


class Page(unittest.TestCase):
    def test_deterministic_with_all_three_parts(self):
        a = issues.render(PROJECTS, "built-1")
        b = issues.render(list(reversed(PROJECTS)), "built-1")
        self.assertEqual(a, b)
        self.assertEqual(a.replace("built-1", "built-2"), issues.render(PROJECTS, "built-2"))
        for part in ("<h2>Timeline</h2>", "<h2>Projects</h2>", "<h2>Metrics</h2>", "prefers-color-scheme:dark"):
            self.assertIn(part, a)
        self.assertLess(a.index(">kiln<"), a.index(">orchard<"))  # most recent activity first
        self.assertNotIn("http", a.replace("http-equiv", ""))  # no external assets
        self.assertIn("<b>23 d</b>", a)
        self.assertIn("<div>4.5 d<small>median</small></div>", a)
        self.assertEqual(a.count("not counted yet"),
                         sum(1 for row in issues.MATRIX.values() for c in row if c and not c[2]))

    def test_matrix_is_complete(self):
        self.assertEqual(len(issues.MATRIX), 5)
        for row in issues.MATRIX.values():
            self.assertEqual(len(row), len(issues.COLUMNS))

    def test_empty(self):
        self.assertIn("No issues found.", issues.render([], "t"))


if __name__ == "__main__":
    unittest.main()
