# Knowledge

The harness learns as it works. This rule says where each new thing goes, so the setup stays small and true as it grows.

## Where things live

- **`CLAUDE.md`** (project root): what the product is, for whom, and why. Structural facts every agent and subagent needs. No process, no lessons, no status journal.
- **Rules** (`.claude/rules/` for this project, `~/.claude/rules/` for every project): how to work. Orchestration, process, conventions. One topic per file, so a rule that is no longer needed can be deleted whole.
- **Issues**: what is planned and in flight (`github-issues.md`).
- **Git**: history. What changed, when, and why.
- **Memory**: where corrections and lessons go first. Save a correction from the owner as a memory, the same day.

## How a rule is born

- Only the owner makes a rule. Nothing becomes a rule automatically, and an agent never decides on its own what goes into one. When the owner says to turn a memory into a rule, write it in the file that owns the topic and delete the memory.
- Before you add anything, look for an existing home. Extend that file before you create a new one.
- One authority per fact. Other files point to it by name and never repeat it. When you find a fact in two places, keep one and cut the other.
- The why goes first in a rule, in one or two sentences. The rules below it follow from it.

## Keep it current

- A rule states the current way only. No dates, no "changed on", no struck-through text, no history sections. Git keeps the history.
- When a rule changes, rewrite it in place.
- Delete a line that adds nothing. When a rule no longer applies, delete the file.
- When a note contradicts a rule, one of them is wrong. Ask the owner, then fix or delete.
- Every change to `CLAUDE.md` or a rule is its own commit, with a message that says why.
