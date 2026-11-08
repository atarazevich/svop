# Knowledge

The harness learns as it works. This rule says where each new thing goes, so the setup stays small and true as it grows.

## Where things live

- **`CLAUDE.md`** (project root): it loads into every session and subagent, so it holds only the contract below.
- **`docs/plan.md`**: the stages (`plan` skill). Only the `plan` skill reads it.
- **`docs/decisions.md`**: every decision with its context, including the replaced ones.
- **Rules** (`.claude/rules/` for this project, `~/.claude/rules/` for every project): how to work. Orchestration, process, conventions. One topic per file, so a rule that is no longer needed can be deleted whole.
- **Issues**: the work items of the plan, and what is in flight (`issues-workflow.md`).
- **Git**: history. What changed, when, and why.
- **Memory**: where corrections and lessons go first. Save a correction from the owner as a memory, the same day.

## The CLAUDE.md contract

`CLAUDE.md` has these sections and nothing else:

1. **About**: what the project is, for whom, and why.
2. **Principles**: what to rely on while building it.
3. **Decisions**: the global decisions in force, one line each. Their context and history are in `docs/decisions.md`.
4. **Story**: who we write for, what we highlight, and why (communication reads it).
5. **Current stage**: one line, the current stage's name and "plan in `docs/plan.md`".

Everything else lives elsewhere: the plan in `docs/plan.md`, decision history in `docs/decisions.md`, how to work in rules, work items in issues, history in git.

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
- Every change to a rule is its own commit, with a message that says why. A change to the plan (`docs/plan.md`, `CLAUDE.md`, the owner pages) is one commit (`plan` skill).
