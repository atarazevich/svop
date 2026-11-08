#!/usr/bin/env python3
"""Build the owner index page (docs/owner/index.html) from CLAUDE.md and docs/plan.md.

Usage: python3 .claude/skills/plan/index.py [project_dir] [--out PATH]

Top: the CLAUDE.md contract sections (About, Principles, Decisions, Story, Current stage).
Below: every stage of docs/plan.md with its status; a stage whose page exists in
docs/owner/stages/<slug>.html links to it. Stdlib only; the same input gives the same page.
"""
import argparse
import html
import re
from pathlib import Path

SECTIONS = ["About", "Principles", "Decisions", "Story", "Current stage"]
STAGE = re.compile(r"^###\s+(?:\d+\.\s+)?(?P<name>.+?)\s+[—-]\s+(?P<status>done|current|next|later)\b.*$", re.I)
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def inline(text):
    t = html.escape(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    def link(m):
        url = m.group(2)
        if re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I) and not re.match(r"^https?:", url, re.I):
            return m.group(1)
        return f'<a href="{url}">{m.group(1)}</a>'
    return re.sub(r"\[([^\]]+)\]\(([^)\s\"]+)\)", link, t)


def render(lines):
    """Paragraphs and lists (bullets or numbers), nested by two-space indent, a sublist inside its item."""
    out, open_items, para = [], [], []  # open_items: list depth -> whether an <li> is open

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    def close_to(level):
        while len(open_items) > level:
            if open_items.pop():
                out.append("</li>")
            out.append("</ul>")

    for raw in lines:
        m = re.match(r"^(\s*)(?:[-*]|\d+\.)\s+(.*)$", raw)
        if m:
            flush()
            level = len(m.group(1)) // 2 + 1
            close_to(level)
            while len(open_items) < level:
                out.append("<ul>")
                open_items.append(False)
            if open_items[-1]:
                out.append("</li>")
            out.append("<li>" + inline(m.group(2)))
            open_items[-1] = True
        elif raw.strip():
            close_to(0)
            para.append(raw.strip())
        else:
            flush()
    flush()
    close_to(0)
    return "\n".join(out)


def claude_sections(text):
    """Map each contract section to its lines. About falls back to the text under the title."""
    found, current, intro, seen_h2 = {}, None, [], False
    for line in text.splitlines():
        if line.startswith("## "):
            seen_h2 = True
            title = line[3:].strip()
            current = next((s for s in SECTIONS if title.lower().startswith(s.lower())), None)
            if current:
                found.setdefault(current, [])
            continue
        if line.startswith("# "):
            continue
        if current:
            found[current].append(line)
        elif not seen_h2:
            intro.append(line)
    if "About" not in found and any(l.strip() for l in intro):
        found["About"] = intro
    return found


def stages(text):
    result, cur = [], None
    for line in text.splitlines():
        m = STAGE.match(line)
        if m:
            cur = {"name": m["name"], "status": m["status"].lower(), "slug": None, "lines": []}
            result.append(cur)
        elif re.match(r"^#{1,3}\s", line):
            cur = None
        elif cur is not None:
            s = re.match(r"^-\s+Slug:\s*(\S+)", line)
            if s:
                cur["slug"] = s.group(1)
            else:
                cur["lines"].append(line)
    for st in result:
        if not (st["slug"] and SLUG.match(st["slug"])):
            print(f"warning: stage '{st['name']}' has no valid '- Slug:' line; using '{slugify(st['name'])}'")
            st["slug"] = slugify(st["name"])
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--out")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    claude = root / "CLAUDE.md"
    plan = root / "docs" / "plan.md"
    out = Path(a.out) if a.out else root / "docs" / "owner" / "index.html"
    secs = claude_sections(claude.read_text()) if claude.exists() else {}
    stg = stages(plan.read_text()) if plan.exists() else []
    name = root.name.replace("-", " ").title()

    parts = []
    for s in SECTIONS:
        body = render(secs[s]) if secs.get(s) and any(l.strip() for l in secs[s]) else '<p class="dim">Not written yet.</p>'
        parts.append(f'<section><h2>{s}</h2>\n{body}</section>')
    rows = []
    for st in stg:
        page = root / "docs" / "owner" / "stages" / f"{st['slug']}.html"
        title = html.escape(st["name"])
        if page.exists():
            title = f'<a href="stages/{st["slug"]}.html">{title}</a>'
        rows.append(f'<details{" open" if st["status"] == "current" else ""}><summary>'
                    f'<span class="st {st["status"]}">{st["status"]}</span> {title}</summary>\n'
                    f'{render(st["lines"])}</details>')
    stage_html = "\n".join(rows) if rows else '<p class="dim">No docs/plan.md yet.</p>'

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(name)} · plan</title>
<style>
:root{{--bg:#fff;--ink:#1d1d1f;--dim:#6e6e73;--line:#e5e5ea;--acc:#b26b00;--done:#2e7d32;--cur:#b26b00}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0f1012;--ink:#e8e6e0;--dim:#a19e97;--line:#2a2c31;--acc:#e3a83f;--done:#7fb58a;--cur:#e3a83f}}}}
body{{margin:0;padding:24px 16px 64px;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,sans-serif}}
main{{max-width:760px;margin:0 auto}} h1{{font-weight:600;font-size:22px;margin:0 0 4px}}
h2{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--acc);margin:28px 0 8px}}
.dim{{color:var(--dim)}} code{{font:13px ui-monospace,Menlo,monospace}} a{{color:var(--acc)}}
details{{border-top:1px solid var(--line);padding:10px 0}} summary{{cursor:pointer;font-weight:500}}
.st{{font:12px ui-monospace,Menlo,monospace;padding:1px 6px;border:1px solid var(--line);border-radius:4px;color:var(--dim)}}
.st.done{{color:var(--done)}} .st.current{{color:var(--cur);border-color:var(--cur)}}
</style></head><body><main>
<h1>{html.escape(name)}</h1><p class="dim">Built from CLAUDE.md and docs/plan.md by the plan skill.</p>
{chr(10).join(parts)}
<section><h2>Stages</h2>
{stage_html}</section>
</main></body></html>
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(out)


if __name__ == "__main__":
    main()
