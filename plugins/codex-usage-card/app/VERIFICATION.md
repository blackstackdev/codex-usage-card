# Verification scope

Version 0.4.0, 7 October 2026 — public beta.

Baseline: one Windows PC, Python 3.11.9 / Tk 8.6 / Codex CLI 0.160.1.

The Cosmic precursor received native visual and pointer/keyboard QA: pin, refresh, corner shrinking/enlarging, keyboard sizing and saved-size relaunch. Its actual registered startup script launched the installed copy; repeat execution retained one instance. A UTF-8 BOM compilation failure was corrected to UTF-16 before success. Installed settings are anchored to the app location. Only the isolated framed QA window was targetable by Computer Use; the normal card is borderless.

Automated release checks cover the eleven existing data/protocol tests, five sizing/startup tests and four plugin-boundary checks (20 total). Native smoke checks one/two limits, stale readings, missing/expired resets, zero/100%, pin persistence and text bounds at widths 360/480/720/960. Startup tests use temporary directories and preserve foreign startup files. CI and package outcomes are recorded in the GitHub release notes after verification.

Other PCs, DPI/monitor arrangements, full keyboard traversal, screen readers, sleep/resume, long unattended use and a full reboot/sign-out cycle remain unverified. A path-with-spaces extraction on this PC is not a fresh-PC acceptance test.

CLI catalog discovery, helper invocation and conversational execution in a fresh Codex host session are distinct. The existing v0.3.0 catalog was discovered successfully; updated manifest checks do not prove a fresh-chat plugin installation. No official plugin-directory submission is claimed.

Screenshot: a real native Cosmic view, with only the QA caption/frame cropped away. The 99% reading is an observed snapshot from 7 October, not a claim about anyone else's account or current balance.
