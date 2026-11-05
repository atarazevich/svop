# Communication Workflow

For a team whose row in teams.yaml lists `communication`. It tells people about the
project one stage at a time, and checks whether it worked.

## Who
- **communication**: plans, drafts and checks. Writes only in docs/communication/.
- **product**: the source. Owns CLAUDE.md and sends the stage events.
- **Owner**: approves plans and posts, publishes the posts, answers in the router.
- **Router**: carries every request to the owner. The subscriber is the project.

## Where
- One file per stage: docs/communication/<stage>.md, with five sections:
  Where, Feedback wanted, Success, Posts, Checks.
- Facts come only from CLAUDE.md, the README and the release notes.
- The owner is asked only through the router, never in a chat.

## Steps
1. **Plan.**
   When: product sends `stage planned: <stage>`.
   Who: communication.
   Does: writes Where (the channels, one line each, with the audience and why),
   Feedback wanted (the one or two things we want to learn) and Success (numbers
   with a date, e.g. "50 stars and 3 issues from strangers in 7 days").
   Out: router `approval` "Plan · <stage>", options Approve / Change, the three
   sections in the body.
   Answers: the owner. Change → redraft from the owner's text, as an update on the
   same request.
2. **Draft.**
   When: product sends `stage done: <stage>`, and the plan for it is approved.
   Who: communication.
   Does: one post per channel, facts only from the sources, with the link to the release.
   Out: router `approval` "Posts · <stage>", options Publish / Edit / Skip, the drafts
   in the body.
   Answers: the owner. Edit → redraft, same request. Skip → write "skipped" under
   Posts, close the request.
3. **Publish.**
   Who: the owner, on the owner's own accounts.
   Then: the owner answers Publish with the post links. Communication writes the links
   and the date under Posts, writes due dates at +1 day and +7 days under Checks, and
   closes the request.
4. **Check.**
   When: a due date has passed (found by the tick).
   Who: communication.
   Does: collects per channel the stars, downloads, issues from strangers, points and
   comments, replies. Writes them under Checks, against Success.
   Out: router `info` "Check day N · <stage>": five lines, the numbers against Success.
   Answers: nobody; info goes to the owner's daily digest.
5. **Signal.**
   When: the day-7 numbers reach less than half of Success, or show something that
   CLAUDE.md does not expect.
   Who: communication → product, message `signal: <stage> — <numbers>, <one line why>`.
   Then: product decides whether to ask the owner (product-workflow.md).

## The tick
Communication runs one session cron every hour. Each tick: read the open router
requests, act on the answered ones, run the checks that are due. After a restart,
create the cron again. The due dates live in the stage files, so a lost tick loses nothing.

## Rules
- Never post in public. Never edit CLAUDE.md or code.
- One router request per step. Follow-ups are updates on the same request.
- No fact without a source in CLAUDE.md, the README or the release notes.
- A step not done, or done another way, is reported to product.
