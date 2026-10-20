# Installing SVOP

This file is for Claude Code. The owner pasted something like "Install SVOP from https://github.com/atarazevich/svop and set up the harness for this project." Follow these steps in order. The owner may not be technical: speak in plain words, one step at a time, and never ask them to run a command you can run yourself.

## 1. Find the project

The project is the folder this session runs in. Refuse only the home folder itself (`~`) and system folders (`/`, `/System`, `/Library`, `/usr`, `/Applications` and the like). Any other folder is fine, including a temporary one. If the session runs in a refused folder, ask the owner which folder the project should live in (it may be new and empty), create it if needed, and use it for every step below.

## 2. Get SVOP

Clone the repository the owner named into `~/.svop`. If `~/.svop` already exists, run `git -C ~/.svop pull`.

## 3. Install what is missing

Check each tool. Install only what is missing.

| Tool | Check | Install |
|---|---|---|
| git | `git --version` | macOS: `xcode-select --install` (a system dialog opens; tell the owner to click Install and wait). Linux: the system package manager. |
| gh (GitHub CLI) | `gh --version` | `brew install gh` if Homebrew is present, otherwise the instructions at https://cli.github.com for this system. |
| herdr | `herdr --version` | `curl -fsSL https://herdr.dev/install.sh \| sh`, or `brew install herdr`. |

The herdr script installs into `~/.local/bin`. If that folder is not on `PATH`, add `export PATH="$HOME/.local/bin:$PATH"` to the shell profile (`~/.zshrc` for zsh, `~/.bashrc` for bash) and to the current shell, then check `herdr --version`.

If an install fails, tell the owner what failed in one sentence and what you will try next.

## 4. GitHub login: the owner's one step

Run `gh auth status`. If it says not logged in, the owner must log in themselves. Ask exactly this:

> Please type `! gh auth login` in this chat and press Enter. Choose GitHub.com, then HTTPS, then "Login with a web browser". Copy the code it shows, paste it in the browser page that opens, and approve. Tell me when it says "Logged in".

If they have no GitHub account, tell them to create a free one at https://github.com/signup first. Then run `gh auth status` again to confirm.

## 5. Git identity

Run `git config --global user.name` and `git config --global user.email`. If either is empty, take the values from `gh api user` (`name` or `login`; `email`, or `<id>+<login>@users.noreply.github.com` when it is null). Tell the owner which name and email you will use and let them change it once. Then set both with `git config --global`.

## 6. Copy the files

```sh
mkdir -p ~/.claude/agents ~/.claude/rules <project>/.claude/rules
```

- `~/.svop/agents/*.md` → `~/.claude/agents/`
- `~/.svop/rules/global/*.md` → `~/.claude/rules/`
- `~/.svop/rules/project/*.md` → `<project>/.claude/rules/`

Before you copy, check each target. If a file with the same name exists and differs, do not overwrite it silently: show the owner what differs in one or two lines and ask whether to replace it. When they say yes, keep the old one as `<name>.md.bak`.

## 7. Describe the product

If the project has no `CLAUDE.md`, ask the owner one question: "What are you making, and for whom?" Write their answer as a short `CLAUDE.md` at the project root: what the product is, who uses it, and why. Nothing else goes there (`knowledge.md`).

## 8. Set up the harness

Follow "Setting up the harness" in `<project>/.claude/rules/team.md`, from step 1. herdr must be running for its step 5: if it is not, ask the owner to open a new terminal window and type `herdr`.

## 9. Hand over

When `team.md` step 8 is done, tell the owner in two or three sentences: what is installed, which teams exist and what each owns, and that from now on they talk only in the `★ orchestrator` tab.
