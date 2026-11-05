# Worktrees and Disk

- A team develops each issue in its own git worktree, on a branch cut from current `origin/main`.
- Build output stays inside the worktree. Never commit it.
- Heavy jobs (builds, test suites) run one at a time across all teams.
- Remove the worktree and its build output once its change has landed on `main`.
- Before you remove a worktree, check that no running process uses a file inside it (`lsof +D <worktree>`).
- Before a heavy job, check free disk space (`df -h .`). Below 10 GB free, stop and tell the orchestrator.
