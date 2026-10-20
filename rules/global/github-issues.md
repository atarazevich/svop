# GitHub Issues

All work is tracked as GitHub issues in the project's repository, with `gh`.

## Two labels

- **`idea`**: needs exploration or discussion before anyone can act on it. The body describes the problem or the opportunity, not the solution. Add thinking as comments over time.
- **`ready`**: explored and scoped. A team can build it without a conversation. The body has three parts:
  - **What**: the change in product terms.
  - **How it fits**: affected files, dependencies, integration points, from an `Explore` pass.
  - **Done when**: acceptance criteria that someone can observe.

## Lifecycle

An issue starts as `idea`. To become `ready`, it needs at least one `Explore` pass. Put the findings and the acceptance criteria in the body, then change the label. A `ready` issue goes to a team (`team.md`). When the work is committed, close the issue with a comment that names the commit.

## Rules

- Create issues with `gh issue create`. When a conversation finds future work, offer an issue.
- Every change to an issue (scope, label, close) gets a comment that says why.
- Check the target repository before any `gh` command that changes something (`gh repo view`).
- When the owner asks "what do we have", list open issues as a table:

| Issue | Stage | Value | Risk | Size |
|---|---|---|---|---|
| #N Title | idea / ready | what it gives if done | what could go wrong or block | S / M / L |
