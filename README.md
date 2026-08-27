Setup steps:

Put check_appointments.py in the repo root (or update the run: path if you nest it).

Put this file at .github/workflows/check-appointments.yml.

Commit an empty known_dates.json (just []) so the first commit-back has something to diff against.

(Optional) In repo Settings → Secrets and variables → Actions, add NOTIFY_WEBHOOK_URL if you want push alerts — Slack incoming webhooks work as-is with the payload shape in the script; for Discord you'd need to change the key from "text" to "content".

** The [skip ci] in the commit message stops the state-update commit from re-triggering other workflows in the repo, if you have any. The contents: write permission is what lets the default GITHUB_TOKEN push that commit — no extra PAT needed.
