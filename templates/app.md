# Template: App

For an app people install, plus the site where they find and download it. Two teams.

## Teams

| Session and tab | Owns | Boundary |
|---|---|---|
| `app` | The app: its code, builds, versions and releases | The only team that ships a new version of the app. |
| `site` | The website and launch material: pages, copy, screenshots, download links | Never changes app code. Facts about the app come from the app team as an issue answer. |

## Rules for both teams

- Work for the other team is an issue in its area, plus one message: `new task: #N`.
- Any screen a user sees goes through a design board the owner approves first (`design-workflow.md`).
