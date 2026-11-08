# Communication Workflow

For a team whose row in teams.yaml lists `communication`. Once a day it looks at
what happened in the project, picks what is worth telling, drafts posts for the
owner, and checks later whether they worked.

## Who
- **communication**: picks, drafts and checks. Writes only in docs/communication/.
- **Plan owner** (the orchestrator, or product if it exists): owns CLAUDE.md, with the Story section (`knowledge.md`).
- **Owner**: approves, publishes the posts on the owner's own accounts, answers in the router.
- **Router**: carries every request to the owner. The project is `project` in teams.yaml.

## Where
- **Core context**: CLAUDE.md, Story first (`knowledge.md`).
- **Cursor**: docs/communication/last-run, two lines: the time and the commit of the last pass.
- **Drafts**: docs/communication/drafts/<YYYY-MM-DD>.md, one file per pass with picks.
- **Posts**: docs/communication/posts.md, one entry per published item: date,
  channel, link, expected reaction, due checks.

## The daily pass
The pass runs headless (`claude -p`). Two things differ from a tab:
- The router channel tools are not loaded. Send with the router's `bus` command:
  `bus out --project <project> --kind <kind> --title=... --description=... --context=... --re=...`.
  A `confirm` lists its options in the description. If `bus` is missing, skip every
  router step and write the message at the end of the drafts file.
- The owner's answers go to the live orchestrator and to the Drive folder `to-router`.
  The next pass reads them there.

Steps, in order:
1. **Story.** If CLAUDE.md has no Story section, or it is empty: send one router
   `confirm` "Story needed · <project>" to the owner, for the plan owner, with what Story
   holds. Draft nothing and leave the cursor. Go to step 8.
2. **Since last time.** Read the cursor. No cursor: take the last 7 days. Sources since then:
   - `git log` since the cursor commit.
   - Issues opened, changed or closed: `gh` in GitHub mode, `docs/issues/` in file mode.
   - Changes to `docs/decisions.md`.
   - Stage pages closed since the cursor (`docs/owner/stages/`, `plan` skill).
   - Router messages: the Drive folders `router-inbox/to-router` (the owner's voice
     requests and answers) and `router-inbox/from-router` (the teams' replies), files
     whose names contain `_<project>`. Use the Google Drive tools. If they are not
     loaded, skip this source.
3. **Pick** at most three items worth telling. Worth it: a finding, an assumption that
   changed, a failure and what we learned, a surprising number. Not worth it: routine
   work, anything not yet understood. No need to wait for results. Each pick names its sources.
4. **Draft** each pick into the drafts file: the material (two lines, with sources),
   why tell it, for whom (from Story), and one draft per channel.
5. **Ask.** One router `confirm` per pick, options Publish / Edit / Skip, the drafts in
   the context. Nothing worth telling: no message.
   - Answers found in step 2: Publish with links → write the entry in posts.md, due
     checks at +1 and +7 days. Edit → redraft from the owner's text, ask again with
     `--re` naming the item. Skip → write "skipped" under the item in its drafts file.
6. **Check** the due entries in posts.md. Per channel, collect the numbers (stars,
   downloads, issues from strangers, points, comments, replies) and write them under
   the entry, against the expected reaction. Send one router `info` "Checks · <project>"
   with one line per entry. A surprise or a miss: `SendMessage` to `product`, text
   `signal: <item> — <numbers>, <one line why>`. If product is not reachable, send a
   router `info` "Signal for product · <project>" with that text, and add the line to
   the drafts file; the orchestrator forwards it to product, or, without a product team, runs `plan` fold on it.
7. **Cursor.** Write the time and `git rev-parse HEAD` to the cursor. Commit the files
   of docs/communication/ that this pass changed, by name, in one commit (git.md).
8. **Log.** End with one line: the date, the items picked, the messages sent, the
   sources skipped, and any step not done or done another way.

## Rules
- Never post in public. Never edit CLAUDE.md or code.
- No fact without a source.
- No secrets, private paths, other people's data or client names in a draft.
- Ask the owner only through the router.
