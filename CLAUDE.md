# SVOP

## Goal

SVOP becomes the normal way a serious Claude Code user runs several projects. Measured by: how many real people set up a factory and brought a project through it, and how many of their stories we showed. Anthropic's attention is a side effect, not the goal.

## About

SVOP is an open-source harness for Claude Code: an orchestrator chat plus teams of AI agents that plan, design, build, review and ship, while the owner only decides. It is a few plain rule, agent and skill files installed into a project's `.claude/` folder.

**The problem SVOP fixes has two parts. These are its cornerstones:**

1. **Scale of autonomy.** How many agents you can leave working without you: you throw in an idea, they go to work, and they come back with something you understand at once.
2. **Readability of the return.** The owner is torn across a million contexts, and the deeper agents go, the murkier what they bring back. SVOP does the opposite: the deeper they went, the clearer they return.

**What SVOP is not.** Starting many projects from a phone and steering them is not the problem; Anthropic already does it (parallel cloud sessions, agent views, dispatch). Their answer is a view of all agents: models, tokens, money. That is ops, and it tells an owner nothing. SVOP packs the ops away and gives the owner an understanding of what is happening and where it is going.

**The boundary with Harness Lens.** Harness Lens makes a Claude Code harness understandable and well laid out: Claude Code only, its native structure (CLAUDE.md, rules, skills, hooks, agents, subagents), teaching while showing your own harness, with no categories of its own. SVOP is one harness; Lens explains any Claude Code harness.

## Principles

- **A task that does not serve this project's goal is not this project's task.** If work goes against a cornerstone, stop and check with the owner. A cornerstone changes only by the owner's deliberate decision.
- **Simple and useful, or not at all.** Everyone already has a mental model of how work gets done. A new concept, file or rule earns its place only if it is clear, simple and helps right away. "You can set up this, and that, and that" sounds nice; it is not the bar. Otherwise leave it out.

## Decisions

## Story

- **Who we write for (hypothesis, under research):** people who already tried parallel Claude Code sessions and hit the wall of supervision: five sessions give not five workers but five things to check. Not beginners, and not people hoping to sell a tool of their own.
- **What stays the same in every post:** one promise that is clear in 10 seconds; the author's real work on the author's own tool; regularity; specifics, failures included; a living voice; one project as the face.
- **A possible post:** what the factory did today, where it stumbled and why, in five sentences and a screenshot.
- **Source:** content comes only from the owner's own words. Nothing is invented for him.

## Current stage
