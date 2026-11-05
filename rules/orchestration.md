# Orchestration

How a session runs its subagents. The pipeline itself is `development-workflow.md`.

- **Never read code yourself.** Code reads, exploration and verification go to a subagent. Markdown is fine.
- **Split big work.** Break a big, broad or unclear task into subtasks a subagent can do alone, and run the independent ones in parallel.
- **Define the output of every dispatch:** a summary under 250 words, bullets, `file:line` for every claim, and `BLOCKED:` at the start when the agent is blocked.
- **Reject vague output.** Send it back with a sharper definition of done.
- **Challenge high-stakes claims.** When a conclusion would change a decision, give it to a second subagent to disprove.
- **No silent skips, no silent workarounds.** A step not done, or done another way, is reported.
