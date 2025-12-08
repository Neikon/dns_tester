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

## Slash Commands
- /commit <message>: Stage tracked changes and create a git commit using the user's name as author.
