# SVOP

**Single owner. Very simple. Opinionated. Product development harness for Claude Code.**

One person, one project, a few markdown files. No config, no options, no installer.

## Why

One Claude Code chat that does everything fills with execution: builds, diffs, review rounds. Soon there is no room left to think about what to build.

SVOP splits the work in two:
- **Discovery.** You and one orchestrator session decide what is worth doing and write it down as a GitHub issue.
- **Execution.** A team session builds the issue with subagents and reports back.

Once a task is defined, you stop following it. The harness carries it to done.

## What you get

- **★ orchestrator**: the one session you talk to. It writes issues, sends them to teams, follows up. It writes no code.
- **◇ teams**: one session per area of your project, each in its own herdr tab. A team runs every issue through the same pipeline.
- **The pipeline**: explore → (design board → critique, for UI work) → develop → three reviewers in parallel → judge → fix → one squashed commit → close the issue.
- **Six agents**: `developer`, `code-reviewer`, `bloat-reviewer`, `ponytail-reviewer`, `designer`, `design-critic`.
- **Rules**: how work moves, how issues are written, how UI is designed before it is built, how worktrees are cleaned up.

## Files

```
agents/             six subagents          → ~/.claude/agents/
rules/global/       pipeline, design, issues → ~/.claude/rules/
rules/project/      team template, worktrees → <your project>/.claude/rules/
```

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code)
- [herdr](https://herdr.dev), a terminal workspace manager for agent sessions
- [gh](https://cli.github.com), logged in (`gh auth login`)
- A project folder. Setup makes it a git repository with a private GitHub remote if it is not one yet.

## Install

```sh
git clone <repo-url> svop
mkdir -p ~/.claude/agents ~/.claude/rules
cp svop/agents/*.md ~/.claude/agents/
cp svop/rules/global/*.md ~/.claude/rules/
mkdir -p <your project>/.claude/rules
cp svop/rules/project/*.md <your project>/.claude/rules/
```

The agents and the global rules go in `~/.claude` and apply to every project you open in Claude Code. The project rules apply to this project only.

`cp` overwrites files with the same name. Check `~/.claude/agents/` and `~/.claude/rules/` first if you already have your own.

## First run

Open herdr. Open Claude Code in your project and say:

> set up the harness

It checks the tools, creates the GitHub repository if needed, creates the `idea` and `ready` labels, proposes the teams for your project and asks you to confirm, then starts the orchestrator and team tabs in herdr. Then switch to the `★ orchestrator` tab.

## Day to day

- Talk only to `★ orchestrator`. Say what you want. It turns that into issues and sends each one to the team that owns the area.
- Teams report back to the orchestrator: done, blocked, or a question with a recommendation. The orchestrator tells you what needs you.
- For a UI change, you approve a design board in the browser before any code is written.
- You can look into a `◇` tab at any time. You never have to.

## What you accept

Teams run with `--permission-mode bypassPermissions` and auto-compact on, so they work without stopping to ask. The orchestrator keeps your own settings. Installing SVOP means accepting that.

## What it is not

- Not for teams of people. One owner decides everything.
- Not configurable. If a rule does not fit your project, edit the markdown.
- Not a framework or a tool. It is instructions for Claude Code.
- Not for GitLab or other trackers. It uses GitHub issues.
