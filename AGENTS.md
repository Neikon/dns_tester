---
name: DNS Tester Agent
description: Agent directives for the DNS_Tester project.
---

## Instructions
- All source code and comments must be written in English, regardless of author.
- Chat conversation should be in Spanish unless explicitly requested otherwise.
- Every piece of code must include comments, even if not authored by the agent.
- Any git commits must always use the user's name as the author.
- When both Adwaita and GTK provide a class for the needed goal, prefer the Adwaita variant.
- Commit messages must always be written in English.
- Even if asked to "make a commit", you may split work into multiple commits when it improves clarity and separates concerns.
- Keep app versioning consistent across meson.build, src/main.py (AboutDialog), and data/es.neikon.dns_tester.metainfo.xml.in.
- On every commit, bump the version using the format YY.MM.DD.hhmm (year’s last two digits, month, day, then hour+minute; omit hhmm if only one bump in the day).
- When bumping version, derive the current date/time yourself by running a terminal command (e.g., `date`) rather than hardcoding it.
- Maintain `CHANGELOG.md` and update it whenever a user-visible change, release-facing fix, or release-management change is introduced.
- Add new changelog notes to the `Unreleased` section while work is in progress.
- When preparing a release, move the relevant `Unreleased` entries into a dated version section, newest first.
- Keep changelog entries concise, grouped by category, and focused on user-visible impact rather than low-level implementation detail.

## Persistent Git Policy
- Codex must manage Git autonomously using GitFlow whenever the repository state allows it.
- This policy is persistent and must remain present in this file; if it is missing or outdated, Codex must update this file as part of the work.
- Repository-specific rules in this file remain mandatory, including English commit messages, user-name authorship, and version bumps on every commit.

### GitFlow Branch Model
- `main`: production code, always stable.
- `develop`: integration branch for ongoing development.
- `feature/*`: new functionality branched from `develop`.
- `bugfix/*`: fixes branched from `develop`.
- `refactor/*`: internal code improvements branched from `develop`.
- `chore/*`: maintenance tasks branched from `develop`.
- `release/*`: release preparation branched from `develop`.
- `hotfix/*`: urgent production fixes branched from `main`.

### GitFlow Rules
- Never do normal development work directly on `main`.
- Use `develop` as the default base branch for continuous development.
- Create a dedicated branch automatically when starting work, choosing the prefix that best matches the task.
- Keep branch naming descriptive and concise, e.g. `feature/add-dot-support` or `chore/update-gitflow-policy`.
- Rebase work branches on top of `develop` before integration when that keeps history cleaner and does not rewrite shared history unexpectedly.
- Merge work into `develop` with `--no-ff` when Codex performs the integration and a merge is appropriate.
- Merge to `main` only from `release/*` or `hotfix/*`.
- When release work is ready, create `release/*` from `develop`, finish the required stabilization, merge it to both `main` and `develop`, and tag the release.
- For urgent production issues, create `hotfix/*` from `main`, merge it back to both `main` and `develop`, and tag the patch release.

### Autonomous Git Decisions
- Codex should create commits autonomously when a stable and coherent milestone is reached.
- Commits must stay small or medium sized, logically grouped, and must not mix unrelated changes.
- Each commit must represent a stable state of the repository.
- Conventional commit prefixes should be used when possible: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, and `test:`.
- Pull requests should target `develop` for `feature/*`, `bugfix/*`, `refactor/*`, and `chore/*` branches when the environment supports PR creation.
- `release/*` and `hotfix/*` branches should be integrated into both `main` and `develop` when the environment supports PR creation.
- Codex is responsible for keeping history clean, avoiding chaotic commits, and avoiding long-lived branches when integration is possible.

## Slash Commands
- /commit <message>: Stage tracked changes and create a git commit using the user's name as author.
