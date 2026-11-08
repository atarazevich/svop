# Git and Worktrees

Work so that no git step ever needs a discard or a delete. The safety hook blocks those, and then only the owner can clean up.

## Never stash

A stash cannot be dropped under the hook, so stashes pile up. Do not stash, even when a hook message suggests it.

## Outputs you do not commit

- A file you only want to look at or compare goes to the session scratchpad, outside the repository. Never write it over a tracked file.
- Write into a tracked file only when you mean to commit the result.
- To compare with the committed version, take the baseline into the scratchpad: `git show HEAD:<path> > <scratchpad>/<file>` for one file, or `git archive HEAD | tar -x -C <scratchpad>/base` for the whole tree, and run the tool there.
- An untracked file in the main checkout is the owner's. Leave it. Inside your own worktree every file is yours: commit it or keep it in gitignored build folders.

## When a hook blocks a git step

Stop. Leave the files as they are, report the path and the blocked command in one line, and go on with what does not depend on it. Never work around the hook.

## Worktrees

- A team that writes no code (product, communication), and the orchestrator for the plan and its pages (`CLAUDE.md`, `docs/owner/`), commit their own files directly on main, by name, with no worktree, and push if the project has a remote.
- A team develops each issue in its own git worktree, on a branch cut from current main (`origin/main` when the project has a remote).
- Build output stays inside the worktree, in gitignored folders. Never commit it.
- Heavy jobs (builds, test suites) run one at a time across all teams.
- Before a heavy job, check free disk space (`df -h .`). Below 10 GB free, stop and tell the orchestrator.

## Landing a change

1. Update main in the checkout that holds it: `git pull --ff-only`, when the project has a remote.
2. In the worktree, rebase the branch on main (`git rebase main`), then squash it: `git reset --soft main`, then one commit.
3. In the checkout that holds main: `git merge --ff-only <branch>`, then push main, when the project has a remote.
4. Check that no running process uses a file in the worktree (`lsof +D <worktree>`), then `git worktree remove <worktree>`.
5. `git branch -d <branch>`.

Never squash-merge or rebase-merge into main, locally or on GitHub: the branch then looks unmerged and `git branch -d` fails.

## Stopping work

Commit everything in the worktree (`git add -A`) as `wip: <why stopped>` and rename the branch: `git branch -m abandoned/<issue>-<slug>`. Then remove the worktree as in step 4. An `abandoned/` branch is a record, not a leftover; it is never deleted.

A worktree must be clean before it is removed: everything landed or on an `abandoned/` branch. Then a plain `git worktree remove` always works.
