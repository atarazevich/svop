# Design Workflow

Any change that adds or changes what a user sees gets a design board before development. Engines, storage and pipelines skip this.

## The cycle

1. **Task.** The issue names the screens and states, the real data to show, and the direction:
   - `fixed`: match the product's current look. The default for an existing product.
   - `open`: the look is not decided. The default for a new surface (a website, onboarding, a new product).
2. **Direction**, only when `open`. The `designer` returns three directions from three design schools and stops. The owner picks one or a mix.
3. **Draw.** The `designer` draws one board in `docs/design/boards/<topic>.html` with real data and the project's tokens, and returns screenshots.
4. **Critique.** The `design-critic` scores the screenshot alone against a named bar. 8 or above passes. Below 8, its fix list and cut list go back to the `designer`. At most three rounds. After the third, show the owner the board and the score.
5. **Approve.** The owner opens the board in the browser and approves a variant or a mix. The words on the board are the contract.
6. **Hand off.** The approved board path goes into the issue. The developer's task says "match this board". Reviewers compare the built UI with the board.

## Rules

- The critic never sees code, the issue or the designer's reasoning. Screenshot only. Run it in a fresh agent, never in the designer's context.
- No board without real data and the project's tokens. No lorem ipsum, no invented colors.
- One board per surface. A change rewrites the board in place. Git keeps the history.
- The board is a spec, not decoration. Beauty is judged by the critic and the owner, not assumed.
