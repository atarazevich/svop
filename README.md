# SVOP

**For anyone who has an idea.**

No course, no bootcamp, no "AI engineering" program. Install it and start building.

SVOP is Claude Code plus a small team of AI agents that plan, build, check and ship. You decide.

<sub>**S**ingle owner · **V**ery simple · **O**pinionated · **P**roduct development harness</sub>

## What you need

- A Mac
- A Claude Pro or Max plan
- An idea

## Start

**1. Install Claude Code.** Open the Terminal app and paste:

```sh
curl -fsSL https://claude.ai/install.sh | bash
```

**2. Hand it SVOP.** Make a folder for your project, open it in Terminal (`cd ` then drag the folder in), type `claude`, and paste:

```
Install SVOP from https://github.com/atarazevich/svop and set up the harness for this project.
```

Claude installs everything else. You log in to Claude and to GitHub, and answer two or three questions: what you are making, which template, and whether to keep your own files.

## What it takes off your shoulders

| **You** | **SVOP** |
|---|---|
| **Say what you want**, in five words or a voice note | Writes it as a task: what is in, what is out, when it is done |
| **Look at a design** and say yes | Draws it, has a critic score it, fixes it before you see it |
| **Test once**, by hand, what no test can | Builds it, each task in its own copy of the project |
| **Decide** the few things only you can | **Three reviewers**: the rules have them check every change before it lands |
| | Version numbers, release notes, cleanup of old copies and disk |
| | Remembers every task in flight, across days away |
| | Reports in one line |

## Proof

| | |
|---|---|
| **16 days** | One orchestrator session, running a live web service. The next four rows are from this session |
| **152** | Owner messages. About 11 a day. 27% were one-liners like "go" or "yes to both" |
| **128 / 111** | Commits shipped / issues closed by the teams in those 16 days |
| **~6** | Times the owner typed into a team's terminal in 16 days |
| **9** | Production incidents the monitor team found, ticketed and saw fixed on its own |
| **~1,000** | Reviewer runs, all projects, since August 2026. 95% of reviews flagged at least one problem before code landed; median 6–7 problems flagged per review |
| **1.4%** | Closed issues reopened: 6 of ~430, all projects, all time |
| **1.5 → 0.3** | "It's broken" messages per day, before SVOP vs with it. Different products, so read it as a direction |

From the author's own products, run with SVOP.
<sub>Source: the author's git history, issue tracker and session logs; two products, 2026.</sub>

## How you work with it

1. **Say it.** "check what I found" → it proposes the work → "go, do everything".
2. **Look at it.** A design board opens in your browser. You say "looks good".
3. **Use it.** One short report, often spoken aloud. You test once.

## How it is organised

```
You
└── ★ orchestrator      the one chat you talk to; writes tasks, follows up, writes no code
    ├── ◇ team (web)    owns one area; runs its own build-and-review
    ├── ◇ team (app)
    └── ◇ team (...)
          explore → design → critic → build → 3 reviewers → fix → land
```

| Part | What it does |
|---|---|
| **★ orchestrator** | Turns what you say into tasks, sends each to its team, tells you only what needs you |
| **◇ team** | One Claude session per area. Builds through helper agents: explore, design, critic, developer, three reviewers |
| **The checks** | By the rules, a design critic scores every screen and three reviewers check every change: correctness, duplication, simplicity |

Teams answer to the orchestrator, never to you. You can look into a `◇` tab. **You never have to.**

## Templates

Setup asks which layout fits and recommends one.

| Template | Teams | For |
|---|---|---|
| [**Web service**](templates/web-service.md) | `backend` API, database, deploys · `agent` the AI your users talk to · `dashboard` your view of it · `monitor` watches production and opens tickets | A service on a server |
| [**App**](templates/app.md) | `app` the app and its releases · `site` website and launch material | Something people install |
| [**Start small**](templates/start-small.md) | `build` owns everything | A new idea. Add a team when a second area appears |

## Compared

| | **Learn first** (a course) | **One AI chat** | **SVOP** |
|---|---|---|---|
| First working result | After the course | The same day | The same day you install it |
| What you must know | The tools, before you start | How to steer it, step by step | What you want |
| Who checks the work | You | You | The rules have a critic and three reviewers check it before it lands |
| When it breaks | You debug | You notice, you ask again | Tracked as a task; a monitor can catch it first |
| What you do all day | Study, then build | Watch it and correct it | Say, look, decide |

## When it goes wrong

The owner noticed their app had stopped taking dictation.

The orchestrator found the cause was its own: it had deleted a copy of the project the running app was started from. It said so, fixed it, and wrote a rule: check that nothing running uses a copy before you delete it ([`worktrees.md`](rules/project/worktrees.md)).

## It keeps itself in order

Every correction you give becomes a rule in its own file. One home per fact, no history in the rules, old rules deleted: [`knowledge.md`](rules/global/knowledge.md).

<details>
<summary><b>What you accept</b></summary>

- **One owner.** For one person who decides everything, not a team of people.
- **GitHub.** Tasks live on GitHub. Setup creates a private repository if your folder has none.
- **Teams act without asking.** They run commands and change files without prompting you, each in its own copy of the project. Your own chat keeps your usual permission prompts.
- **Usage.** Several teams at once use more of your plan's limit. Max suits daily work.
- **No settings.** SVOP is a few plain text files. If a rule does not fit, edit the file.

</details>

<details>
<summary><b>What it changes on your computer, and how to remove it</b></summary>

**Adds**

- Six agent files and four rule files in `~/.claude/` (Claude Code's hidden settings folder). An existing file with the same name is kept as `<name>.md.bak`.
- Two rule files in your project's `.claude/rules/`, and a short `CLAUDE.md` if there is none.
- Two GitHub labels: `idea` and `ready`.
- The tools `gh` and `herdr`, if missing. herdr shows each Claude session as a tab.
- A copy of this repository in `~/.svop`.

**Remove**

1. Delete the files listed under Files from `~/.claude/` and from your project's `.claude/rules/`.
2. Rename any `.bak` file back.
3. Delete `CLAUDE.md` if setup created it, and `~/.svop`.
4. `gh label delete idea` and `gh label delete ready`.
5. Optional: `brew uninstall herdr gh`.

</details>

<details>
<summary><b>Files</b></summary>

```
INSTALL.md          the steps Claude follows to install SVOP
agents/             six agents → ~/.claude/agents/
                    developer, code-reviewer, bloat-reviewer,
                    ponytail-reviewer, designer, design-critic
rules/global/       four rules → ~/.claude/rules/
                    development-workflow, design-workflow,
                    github-issues, knowledge
rules/project/      two rules  → <your project>/.claude/rules/
                    team, worktrees
templates/          team layouts setup offers
                    web-service, app, start-small
```

</details>

MIT license. See [LICENSE](LICENSE).
