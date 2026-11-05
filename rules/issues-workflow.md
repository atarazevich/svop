# Issues Workflow

All work is tracked as issues. A project with a GitHub remote keeps them on GitHub, with `gh` (GitHub mode). A project without one keeps them as files in `docs/issues/` (file mode).

## Two states

- **`idea`**: needs exploration or discussion before anyone can act on it. The body describes the problem or the opportunity, not the solution. Add thinking as comments over time.
- **`ready`**: explored and scoped. A team can build it without a conversation. The body has three parts:
  - **What**: the change in product terms.
  - **How it fits**: affected files, dependencies, integration points, from an `Explore` pass.
  - **Done when**: acceptance criteria that someone can observe.

## GitHub mode

- The state is a label: `idea` or `ready`.
- Create issues with `gh issue create`.
- Check the target repository before any `gh` command that changes something (`gh repo view`).
- A stage is a milestone. Each issue is in the milestone of its stage. A stage is done when all its issues are closed.

## File mode

- One file per issue: `docs/issues/<N>-<short-name>.md`. `N` is the next free number.
- The file starts with frontmatter:
  ```
  ---
  status: idea | ready | done
  stage: <stage>
  ---
  ```
- The body has the same parts as on GitHub. Comments go at the end of the file, each under a dated line.
- To close an issue, set `status: done`.
- A stage is the `stage:` field. A stage is done when all its issues are `done`.

## Lifecycle

An issue starts as `idea`. To become `ready`, it needs at least one `Explore` pass. Put the findings and the acceptance criteria in the body, then change the state. A `ready` issue goes to a team (`team.md`). When the work is committed, close the issue with a comment that names the commit.

## Rules

- When a conversation finds future work, offer an issue.
- Every change to an issue (scope, state, close) gets a comment that says why.
- When the owner asks "what do we have", list open issues as a table:

| Issue | State | Value | Risk | Size |
|---|---|---|---|---|
| #N Title | idea / ready | what it gives if done | what could go wrong or block | S / M / L |
