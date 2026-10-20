# Development Workflow

A team builds each task through subagents. The task is an issue (`github-issues.md`). Without an issue there is no developer run.

## The pipeline

1. **Explore.** Run the built-in `Explore` agent. It maps the affected files, their dependencies and the integration points. Before an issue is `ready`, the findings go into the issue body. Before development, they go to the developer as context.
2. **Design**, only for a user-visible UI change: `design-workflow.md`. The approved board goes into the issue.
3. **Develop.** Give the `developer` agent the issue and the exploration context. Give the problem, not a recipe.
4. **Review.** After the developer commits, run three reviewers in parallel with the commit hash and the issue:
   - `code-reviewer`: correctness (spec, types, references).
   - `bloat-reviewer`: economy against the repository (fix-commit shape, duplication, new abstractions).
   - `ponytail-reviewer`: simplicity of the code itself (delete, stdlib, native, yagni, shrink).
5. **Judge.** Reviewers are adversaries, not authorities. Their findings are proposals. Accept a finding when it removes real excess or a real fault at no cost to correctness, clarity or a behavior the issue asks for. Reject it in one line when it trades a real concern for brevity. A test, a required validator or a guard at a trust boundary is not bloat.
6. **Fix.** Send only the accepted findings back to the developer, with the issue and the context. Repeat steps 4 to 6 at most three times. After the third round, report what is still open.
7. **Squash and commit.** One logical change is one commit. Squash the develop-review-fix commits of one change into one before you push. Different changes stay separate commits. The message says what changed and why, and references the issue (`#N`).
8. **Close.** Close the issue with a comment that names the commit.

## When not to use the pipeline

The owner says exactly what to change: a config value, a file move, git housekeeping, a typo. Do it directly. Still commit with a clear message.

## Research is not development

When the owner wants to think, compare or explore, do research and discuss. Do not touch code. The pipeline starts only when the owner approves a defined task.

## Rules

- No developer run without an issue. Write the issue first.
- Explore before develop.
- Review before push, never after.
- The developer gets only the findings that passed the judge step.
- No `Co-Authored-By` or tool attribution lines in commit messages.
