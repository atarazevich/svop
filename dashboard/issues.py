#!/usr/bin/env python3
"""Every project's issues over time, and the metrics matrix, as one self-contained HTML page.

Usage: python3 dashboard/issues.py [--root ~/Projects] [--out <path>] [--owner <login>]

Reads, by code only and never writing to a project:
- GitHub issues of a repository with a GitHub remote (`gh issue list`, reopens from the first 20 pages of
  `gh api .../issues/events`). A clone of someone else's repository is skipped: its GitHub owner must be
  the owner (`--owner`, default the gh user) or an organisation the gh user administers;
- issue files `docs/issues/*.md` from git history (author dates): created when added, closed when the
  frontmatter says `status: done` or the file is deleted, reopened when a later commit moves it back from
  done; a renamed file stays the same issue. A file added already done has no start date: it counts as
  closed but stays out of the median.
The page shows private project names: it is for the owner only. Same input gives the same page,
except the one "built at" line.
"""
import argparse
import html
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Set, Tuple

# The matrix. Rows are metrics, columns are teams. A cell is (what is counted, source, key) or None for "—".
# key names a number this script computes ("cycle", "reopens"); None means "not counted yet".
COLUMNS = ["Overall", "Development", "Design", "Communication", "Monitor", "Orchestrator"]
MATRIX: Dict[str, List[Optional[Tuple[str, str, Optional[str]]]]] = {
    "Owner touches per closed issue": [
        ("owner messages per closed issue", "router log, session transcripts", None),
        ("owner messages in team sessions per closed issue", "session transcripts", None),
        ("owner comments per approved design", "issues, router log", None),
        ("owner messages per piece sent", "router log", None),
        ("owner replies per alert", "router log", None),
        ("owner messages per issue made ready", "session transcripts", None),
    ],
    "Cycle time": [
        ("median days, opened to closed", "issues", "cycle"),
        ("median days, ready to landed on main", "issues, git", None),
        ("median days, opened to approved", "issues", None),
        None,
        ("median days, alert to fix landed", "router log, git", None),
        ("median days, idea to ready", "issues", None),
    ],
    "Cost per closed issue": [
        ("$ of tokens per closed issue", "session transcripts", None),
        ("$ in team sessions per closed issue", "session transcripts", None),
        ("$ per approved design", "session transcripts", None),
        ("$ per piece sent", "session transcripts", None),
        ("$ per run", "session transcripts", None),
        ("$ per issue made ready", "session transcripts", None),
    ],
    "Review rounds per issue": [
        ("review-and-fix rounds per closed issue", "session transcripts", None),
        ("reviewer passes before landing", "session transcripts", None),
        ("critic rounds before approval", "issues", None),
        None,
        None,
        None,
    ],
    "Reopens": [
        ("issues reopened, all projects", "issues", "reopens"),
        ("issues reopened after landing", "issues, git", None),
        ("approved designs reopened", "issues", None),
        None,
        None,
        ("issues sent back from ready to idea", "issues", None),
    ],
}


class Issue(NamedTuple):
    created: datetime
    closed: Optional[datetime]
    reopens: int
    started: bool = True  # False: added already done, so the opened-to-closed time is unknown


def order(i: Issue) -> Tuple[datetime, datetime, int]:
    return i.created, i.closed or datetime.max.replace(tzinfo=timezone.utc), i.reopens


class Project(NamedTuple):
    name: str
    issues: List[Issue]


Runner = Callable[[List[str], Optional[Path]], Optional[str]]


def run(cmd: List[str], cwd: Optional[Path] = None) -> Optional[str]:
    """Stdout of a read-only command, or None when it fails."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def moment(stamp: str) -> datetime:
    """A UTC time from an ISO timestamp (git %cI or GitHub's ...Z)."""
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc)


# ---- finding repositories ----

def is_repo(folder: Path) -> bool:
    return (folder / ".git").exists()


def find_repos(root: Path, runner: Runner = run) -> Tuple[Dict[str, List[Path]], List[Tuple[str, str]]]:
    """Project name -> its repositories, and (folder, reason) for every folder skipped.

    A project folder is a repository, or holds repositories one level down. Symlinks are followed.
    Worktrees and second checkouts of one repository count once, under the main checkout.
    """
    found: List[Tuple[str, Path, str]] = []  # (project, repo, git common dir)
    skipped: List[Tuple[str, str]] = []
    for entry in sorted(root.iterdir()):
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        repos = [entry] if is_repo(entry) else sorted(
            p for p in entry.iterdir() if not p.name.startswith(".") and p.is_dir() and is_repo(p))
        if not repos:
            skipped.append((entry.name, "not a git repository"))
            continue
        for repo in repos:
            common = runner(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], repo)
            found.append((entry.name, repo, os.path.realpath(common.strip()) if common else str(repo.resolve())))
    owner: Dict[str, Tuple[str, Path]] = {}
    for name, repo, common in found:
        main = os.path.realpath(repo / ".git") == common
        if common not in owner or (main and os.path.realpath(owner[common][1] / ".git") != common):
            owner[common] = (name, repo)
    projects: Dict[str, List[Path]] = {}
    for name, repo in sorted(owner.values()):
        projects.setdefault(name, []).append(repo)
    for name in sorted({n for n, _, _ in found} - set(projects)):
        skipped.append((name, "worktree or second checkout of another project's repository"))
    return projects, skipped


# ---- GitHub issues ----

def github_slug(repo: Path, runner: Runner = run) -> Optional[str]:
    names = (runner(["git", "remote"], repo) or "").split()
    for remote in sorted(names, key=lambda n: n != "origin"):
        url = runner(["git", "remote", "get-url", remote], repo) or ""
        m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url.strip())
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    return None


def owners(owner: str, runner: Runner = run) -> Set[str]:
    """The owner's login and the organisations the gh user administers, lower-cased."""
    orgs = runner(["gh", "api", "user/memberships/orgs", "--paginate",
                   "--jq", '.[] | select(.role == "admin") | .organization.login'], None) or ""
    return {owner.lower(), *orgs.lower().split()}


MAX_PAGES = 20  # issue events pages of 100 read per repository
MAX_ISSUES = 1000


def reopens(slug: str, runner: Runner = run) -> Tuple[Dict[int, int], Optional[str]]:
    """Reopen count per issue number, and a note when the count is incomplete."""
    counts: Dict[int, int] = {}
    for page in range(1, MAX_PAGES + 1):
        out = runner(["gh", "api", f"repos/{slug}/issues/events?per_page=100&page={page}",
                      "--jq", 'length, (.[] | select(.event == "reopened") | .issue.number)'], None)
        if out is None:
            return counts, f"reopens incomplete (gh failed on page {page})"
        size, *numbers = out.split()
        for n in numbers:
            counts[int(n)] = counts.get(int(n), 0) + 1
        if int(size) < 100:
            return counts, None
    return counts, f"reopens incomplete (stopped after {MAX_PAGES} pages of issue events)"


def gh_trouble(cmd: List[str]) -> str:
    """Why a gh command failed, in gh's own words (it is run again to read its message)."""
    if shutil.which("gh") is None:
        return "gh not installed"
    try:
        err = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        err = str(e)
    line = err.splitlines()[0] if err else "no message from gh"
    if re.search(r"auth login|not logged|authenticat|rate limit", line, re.IGNORECASE):
        return f"gh not logged in or rate-limited: {line}"
    return f"repository not readable: {line}"


def gh_issues(slug: str, runner: Runner = run,
              trouble: Callable[[List[str]], str] = gh_trouble) -> Tuple[Optional[List[Issue]], List[str]]:
    """GitHub issues of one repository (None when gh cannot read it), and notes on what is missing."""
    cmd = ["gh", "issue", "list", "-R", slug, "--state", "all", "--limit", str(MAX_ISSUES),
           "--json", "number,title,state,createdAt,closedAt,labels,milestone"]
    listed = runner(cmd, None)
    if listed is None:
        return None, [trouble(cmd)]
    rows = json.loads(listed)
    notes = [f"first {MAX_ISSUES} issues only"] if len(rows) >= MAX_ISSUES else []
    reopened, note = reopens(slug, runner)
    notes += [note] if note else []
    return [Issue(moment(i["createdAt"]), moment(i["closedAt"]) if i.get("closedAt") else None,
                  reopened.get(i["number"], 0))
            for i in sorted(rows, key=lambda i: i["number"])], notes


# ---- issue files ----

MARK = "\x01"
STATUS = re.compile(r"status:\s*[\"']?([\w-]+)", re.IGNORECASE)


def frontmatter_status(lines: List[str]) -> Optional[str]:
    """The `status:` value inside the leading `---` block, lower-cased."""
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        m = STATUS.match(line)
        if m:
            return m.group(1).lower()
    return None


class FileDiff(NamedTuple):
    src: Optional[str]  # path before the commit, None when added
    dst: Optional[str]  # path after the commit, None when deleted
    content: Optional[List[str]]  # the whole new file, None when the diff has no hunk (pure rename, mode)


def file_diffs(block: List[str]) -> List[FileDiff]:
    """One commit's `-p -M -U<large>` output, split per file. Full context makes each hunk the whole file."""
    diffs: List[FileDiff] = []
    for start in [k for k, line in enumerate(block) if line.startswith("diff --git ")]:
        a, _, b = block[start][len("diff --git a/"):].rpartition(" b/")
        src: Optional[str] = a
        dst: Optional[str] = b
        content: Optional[List[str]] = None
        for line in block[start + 1:]:
            if line.startswith("diff --git "):
                break
            if content is not None:
                if line[:1] in (" ", "+"):
                    content.append(line[1:])
            elif line.startswith("new file mode"):
                src = None
            elif line.startswith("deleted file mode"):
                dst = None
            elif line.startswith("rename from "):
                src = line[len("rename from "):]
            elif line.startswith("rename to "):
                dst = line[len("rename to "):]
            elif line.startswith("@@"):
                content = []
        diffs.append(FileDiff(src, dst, content))
    return diffs


def parse_issue_log(text: str) -> List[Issue]:
    """Issues from `git log --reverse -M -p -U<large>` over docs/issues, each commit headed by MARK + ISO date."""
    issues: List[Issue] = []
    live: Dict[str, List] = {}  # path -> [created, closed, reopens, started]
    for commit in text.split(MARK)[1:]:
        lines = commit.splitlines()
        when = moment(lines[0].strip())
        for d in file_diffs(lines[1:]):
            if d.dst is None:  # deleted: closed then, unless already done
                if d.src in live:
                    created, closed, reopens, started = live.pop(d.src)
                    issues.append(Issue(created, closed or when, reopens, started))
                continue
            added = d.src not in live
            rec = [when, None, 0, True] if added else live.pop(d.src)
            live[d.dst] = rec
            if d.content is None:
                continue
            if frontmatter_status(d.content) == "done":
                if rec[1] is None:
                    rec[1] = when
                    rec[3] = rec[3] and not added
            elif rec[1] is not None:
                rec[1], rec[2] = None, rec[2] + 1
    issues += [Issue(*rec) for rec in live.values()]
    return sorted(issues, key=order)


def file_issues(repo: Path, runner: Runner = run) -> List[Issue]:
    log = runner(["git", "-c", "core.quotePath=false", "log", "--reverse", "-M", f"--format={MARK}%aI",
                  "-p", "-U100000", "--", "docs/issues/*.md"], repo)
    return parse_issue_log(log) if log else []


# ---- gathering ----

def gather(root: Path, allowed: Set[str], runner: Runner = run) -> Tuple[List[Project], List[Tuple[str, str]]]:
    """Projects with issues, from repositories whose GitHub owner is in `allowed` or that have no GitHub remote."""
    repos, skipped = find_repos(root, runner)
    projects: List[Project] = []
    seen = set()
    for name, paths in repos.items():
        issues: List[Issue] = []
        kept = 0
        for repo in paths:
            label = name if repo.name == name else f"{name}/{repo.name}"
            slug = github_slug(repo, runner)
            if slug and slug.split("/")[0].lower() not in allowed:
                skipped.append((label, "not the owner's repository"))
                continue
            kept += 1
            issues += file_issues(repo, runner)
            if slug and slug not in seen:
                seen.add(slug)
                got, notes = gh_issues(slug, runner)
                skipped += [(f"{label} (GitHub)", note) for note in notes]
                issues += got or []
        if not kept:
            continue
        if issues:
            projects.append(Project(name, sorted(issues, key=order)))
        else:
            skipped.append((name, "no issues"))
    return projects, sorted(skipped)


# ---- numbers ----

def monday(t: datetime) -> date:
    return t.date() - timedelta(days=t.weekday())


def last_activity(p: Project) -> datetime:
    return max(max(i.created, i.closed or i.created) for i in p.issues)


def weeks(projects: List[Project]) -> List[date]:
    times = [t for p in projects for i in p.issues for t in (i.created, i.closed) if t]
    first, last = monday(min(times)), monday(max(times))
    return [first + timedelta(weeks=k) for k in range((last - first).days // 7 + 1)]


def per_week(times: List[datetime], axis: List[date]) -> List[int]:
    index = {w: k for k, w in enumerate(axis)}
    counts = [0] * len(axis)
    for t in times:
        counts[index[monday(t)]] += 1
    return counts


def open_at_week_end(issues: List[Issue], axis: List[date]) -> List[int]:
    ends = [datetime.combine(w + timedelta(weeks=1), datetime.min.time(), timezone.utc) for w in axis]
    return [sum(1 for i in issues if i.created < e and (i.closed is None or i.closed >= e)) for e in ends]


def median_days(issues: List[Issue]) -> Optional[float]:
    spans = [(i.closed - i.created).total_seconds() / 86400 for i in issues if i.closed and i.started]
    return statistics.median(spans) if spans else None


def fmt_days(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:.1f} d" if v < 10 else f"{v:.0f} d"


# ---- page ----

CSS = """
:root{--bg:#fbfaf7;--fg:#22252a;--mute:#6b7078;--line:#e4e1da;--card:#fff;--open:#3b6fb6;--close:#5f9e7a;--area:#3b6fb633}
@media (prefers-color-scheme:dark){:root{--bg:#16181b;--fg:#e6e4df;--mute:#9a9ea6;--line:#2c3036;--card:#1d2024;--open:#7fa8e0;--close:#86c29f;--area:#7fa8e033}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-variant-numeric:tabular-nums}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:15px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:36px 0 12px}
.sub{color:var(--mute);font-size:13px}
.kpis{display:flex;flex-wrap:wrap;gap:8px 28px;margin:18px 0 0}
.kpi b{display:block;font-size:26px;font-weight:600}.kpi span{color:var(--mute);font-size:13px}
.row{display:grid;grid-template-columns:150px 1fr 330px;gap:12px;align-items:center;padding:8px 0;border-top:1px solid var(--line)}
.row:first-of-type{border-top:0}
.name{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nums{display:grid;grid-template-columns:repeat(6,1fr);gap:4px;text-align:right;font-size:13px}
.nums div{white-space:nowrap}.nums small{display:block;color:var(--mute);font-size:11px}
.note{display:block;font-weight:400;font-size:11px;color:var(--mute);white-space:normal}
.head{color:var(--mute);font-size:12px}
.chart{position:relative}
svg{display:block;width:100%}
.ticks{position:relative;height:16px;font-size:11px;color:var(--mute)}
.ticks span{position:absolute;top:2px;white-space:nowrap}
.lbl{font-size:12px;color:var(--mute)}
.lbl i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-top:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}
th{font-weight:600}thead th{color:var(--mute);font-weight:500;border-top:0}
td b{font-size:17px;font-weight:600;display:block}
td .src{color:var(--mute);font-size:11px;display:block}
td.na{color:var(--mute)}
.scroll{overflow-x:auto}
@media (max-width:760px){main{padding:16px 12px 32px}.row{grid-template-columns:1fr;gap:4px}.nums{font-size:12px;grid-template-columns:repeat(6,auto);justify-content:space-between}
.nums small{font-size:10px}.row .lbl{display:flex;gap:12px}.ticks .m{display:none}table{min-width:720px}.head .nums,.row>div:empty{display:none}}
"""


def ticks(axis: List[date]) -> str:
    step = 1 if len(axis) <= 30 else 3 if len(axis) <= 120 else 12
    spans, last = [], None
    for k, w in enumerate(axis):
        month = (w.year, w.month)
        if month != last and (w.month - 1) % step == 0:
            label = str(w.year) if step == 12 else w.strftime("%b %Y" if k == 0 or w.month == 1 else "%b")
            cls = "" if k == 0 or w.month == 1 else ' class="m"'
            spans.append(f'<span{cls} style="left:{100 * k / len(axis):.2f}%">{label}</span>')
        last = month
    return f'<div class="ticks">{"".join(spans)}</div>'


def flow_svg(opened: List[int], closed: List[int], axis: List[date], height: int = 120) -> str:
    """Opened per week above the midline, closed below, one column per week."""
    top = max(opened + closed + [1])
    half = height / 2
    bars = []
    for k, (o, c) in enumerate(zip(opened, closed)):
        tip = f"<title>week of {axis[k].isoformat()}: {o} opened, {c} closed</title>"
        if o:
            h = half * o / top
            bars.append(f'<rect x="{k + .12:.2f}" y="{half - h:.2f}" width=".76" height="{h:.2f}" fill="var(--open)">{tip}</rect>')
        if c:
            h = half * c / top
            bars.append(f'<rect x="{k + .12:.2f}" y="{half:.2f}" width=".76" height="{h:.2f}" fill="var(--close)">{tip}</rect>')
    return (f'<svg viewBox="0 0 {len(axis)} {height}" preserveAspectRatio="none" style="height:{height}px" role="img" '
            f'aria-label="issues opened and closed per week">'
            f'<line x1="0" x2="{len(axis)}" y1="{half}" y2="{half}" stroke="var(--line)" vector-effect="non-scaling-stroke"/>'
            f'{"".join(bars)}</svg>')


def open_svg(counts: List[int], height: int = 70) -> str:
    top = max(counts + [1])
    pts = " ".join(f"{k + .5:.1f},{height - (height - 4) * c / top:.2f}" for k, c in enumerate(counts))
    n = len(counts)
    return (f'<svg viewBox="0 0 {n} {height}" preserveAspectRatio="none" style="height:{height}px" role="img" '
            f'aria-label="open issues over time">'
            f'<polygon points="0,{height} {pts} {n},{height}" fill="var(--area)"/>'
            f'<polyline points="{pts}" fill="none" stroke="var(--open)" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>')


def strip_svg(counts: List[int], top: int, height: int = 26) -> str:
    bars = "".join(f'<rect x="{k + .12:.2f}" y="{height - max(1.5, height * c / top):.2f}" width=".76" '
                   f'height="{max(1.5, height * c / top):.2f}" fill="var(--open)"/>'
                   for k, c in enumerate(counts) if c)
    return (f'<svg viewBox="0 0 {len(counts)} {height}" preserveAspectRatio="none" style="height:{height}px">'
            f'<line x1="0" x2="{len(counts)}" y1="{height - .5}" y2="{height - .5}" stroke="var(--line)" '
            f'vector-effect="non-scaling-stroke"/>{bars}</svg>')


def unstarted(p: Project) -> str:
    n = sum(1 for i in p.issues if not i.started)
    return f'<small class="note">{n} without a start date, left out of the median</small>' if n else ""


def nums(cells: List[Tuple[str, str]]) -> str:
    return '<div class="nums">' + "".join(f"<div>{v}<small>{k}</small></div>" for v, k in cells) + "</div>"


def matrix_html(values: Dict[str, str]) -> str:
    head = "".join(f"<th>{c}</th>" for c in COLUMNS)
    rows = []
    for metric, cells in MATRIX.items():
        tds = []
        for cell in cells:
            if cell is None:
                tds.append('<td class="na">—</td>')
                continue
            what, source, key = cell
            if key:
                tds.append(f"<td><b>{values[key]}</b>{what}<span class=\"src\">from {source}</span></td>")
            else:
                tds.append(f"<td>{what}<span class=\"src\">not counted yet · needs {source}</span></td>")
        rows.append(f"<tr><th>{metric}</th>{''.join(tds)}</tr>")
    return f'<div class="scroll"><table><thead><tr><th></th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def render(projects: List[Project], built_at: str) -> str:
    projects = sorted(projects, key=lambda p: (-last_activity(p).toordinal(), p.name))
    every = [i for p in projects for i in p.issues]
    if not every:
        body = "<p>No issues found.</p>"
    else:
        axis = weeks(projects)
        opened = per_week([i.created for i in every], axis)
        closed = per_week([i.closed for i in every if i.closed], axis)
        span = f"{axis[0].isoformat()} to {(axis[-1] + timedelta(days=6)).isoformat()}, {len(axis)} weeks"
        n_open = sum(1 for i in every if i.closed is None)
        reopens = sum(i.reopens for i in every)
        cycle = fmt_days(median_days(every))
        kpis = [(len(projects), "projects"), (len(every), "issues"), (n_open, "open now"),
                (len(every) - n_open, "closed"), (cycle, "median opened→closed"), (reopens, "reopens")]
        legend = ('<div class="lbl"><div><i style="background:var(--open)"></i>opened</div>'
                  '<div><i style="background:var(--close)"></i>closed</div></div>')
        timeline = (
            f'<div class="row"><div>{legend}<div class="lbl">peak {max(opened + closed)} / week</div></div>'
            f'<div class="chart">{flow_svg(opened, closed, axis)}</div>'
            f'{nums([(sum(opened), "opened"), (sum(closed), "closed"), (max(opened), "peak opened")])}</div>'
            f'<div class="row"><div class="lbl">open issues<br>peak {max(open_at_week_end(every, axis))}</div>'
            f'<div class="chart">{open_svg(open_at_week_end(every, axis))}{ticks(axis)}</div>'
            f'{nums([(n_open, "open now")])}</div>')
        strips = [per_week([i.created for i in p.issues], axis) for p in projects]
        top = max(max(s) for s in strips)
        rows = [f'<div class="row head"><div>project</div><div>opened per week · tallest bar = {top}</div>'
                f'<div></div></div>']
        for p, strip in zip(projects, strips):
            p_open = sum(1 for i in p.issues if i.closed is None)
            rows.append(
                f'<div class="row"><div class="name" title="{html.escape(p.name)}">{html.escape(p.name)}{unstarted(p)}</div>'
                f'<div class="chart">{strip_svg(strip, top)}</div>'
                + nums([(len(p.issues), "opened"), (len(p.issues) - p_open, "closed"), (p_open, "open"),
                        (fmt_days(median_days(p.issues)), "median"), (sum(i.reopens for i in p.issues), "reopens"),
                        (f"{last_activity(p):%d %b}" if last_activity(p).year == axis[-1].year
                         else f"{last_activity(p):%d %b %y}", "last")])
                + "</div>")
        rows.append(f'<div class="row"><div></div><div>{ticks(axis)}</div><div></div></div>')
        body = (
            '<div class="kpis">' + "".join(f'<div class="kpi"><b>{v}</b><span>{k}</span></div>' for v, k in kpis)
            + f'</div><h2>Timeline</h2><p class="sub">Per week, all projects together, {span}. Weeks start on Monday, UTC.</p>{timeline}'
            + '<h2>Projects</h2><p class="sub">Most recent activity first. Same weeks as the timeline. '
            + 'Median is days from opened to closed.</p>' + "".join(rows)
            + '<h2>Metrics</h2><p class="sub">Watched, never optimised.</p>'
            + matrix_html({"cycle": cycle, "reopens": str(reopens)}))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="color-scheme" content="light dark"><title>Issues</title>'
            f'<style>{CSS}</style></head><body><main><h1>Issues</h1>'
            f'<div class="sub">built at {html.escape(built_at)}</div>{body}</main></body></html>\n')


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default="~/Projects", help="folder holding the project folders")
    ap.add_argument("--out", default="~/Downloads/issues-dashboard.html", help="where to write the page")
    ap.add_argument("--owner", help="GitHub login whose repositories count (default: the gh user)")
    args = ap.parse_args(argv)
    owner = args.owner or (run(["gh", "api", "user", "--jq", ".login"]) or "").strip()
    if not owner:
        print("cannot tell the owner: log in with `gh auth login` or pass --owner", file=sys.stderr)
        return 1
    projects, skipped = gather(Path(args.root).expanduser(), owners(owner))
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(projects, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")))
    print(f"{len(projects)} projects, {sum(len(p.issues) for p in projects)} issues -> {out}")
    for name, reason in skipped:
        print(f"skipped {name}: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
