---
name: usage-card
description: Use when the user asks to show their Codex plan limits, remaining usage or reset times, or to open the Usage Card for Codex Windows desktop widget.
---

# Usage Card for Codex

Use the bundled local helper. From the directory containing this SKILL.md, go up two levels to the plugin root: `skills/usage-card/../..`. The helper is `<plugin-root>/scripts/usage.py`. Quote the absolute path when invoking it; never interpolate user input into a command.

## Show limits

Run `python "<plugin-root>/scripts/usage.py" status`. If Python is unavailable, explain that Python 3.11+ with Tk is required; do not install dependencies without a user request.

On success, summarize each returned window's remaining percentage and reset time using the user's local timezone. `minutes=10080` means Weekly; `minutes=300` means 5-hour. Null duration or reset is unknown. Report the observation as a snapshot; shared account limits are not specific to this chat. Only show windows actually returned. Never infer 100% after a reset or fabricate a missing short window.

On failure, relay the helper's generic error and suggest checking sign-in in the Codex app. Do not inspect auth files, print raw server responses, reconnect accounts, redeem reset credits or run a model turn.

## Open the desktop card

Only when the user asks to open the card, run `python "<plugin-root>/scripts/usage.py" open`. The helper supports Windows, requires pythonw with Tk and reuses the widget's single-instance protection. A successful launch request does not prove the window appeared: report it as requested, or already running when exit code indicates that; do not claim visual verification. The user can double-click `app/Launch Widget.vbs` as a fallback.

Opening the card does not enable startup. The card refreshes every five minutes while open. Close or Escape exits it; Pin keeps it above other windows. Drag its lower-right corner to resize; placement, width and pin preference are saved locally. Menu → Size offers presets.

Startup is opt-in under Menu → Launch at Windows sign-in. Do not enable it unless the user explicitly requests startup. It installs a stable local app copy and a dedicated, reversible per-user Startup-folder entry. No scheduled tasks or administrator rights are needed. A user-authorized command-line setup uses `python "<plugin-root>/app/cosmic.py" --enable-startup`; disabling uses `--disable-startup`. The status/open helper never changes this setting.
