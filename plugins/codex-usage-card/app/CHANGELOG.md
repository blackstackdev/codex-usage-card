# Changelog

## 0.4.0 — 2026-10-07

Cosmic desktop card — public beta.

- Added a blue planet backdrop, large remaining percentage and visible local reset date.
- Added lower-right resizing, proportional artwork/text/controls, saved width, size presets and keyboard sizing.
- Added opt-in Windows sign-in startup, stable local installation and reversible per-user startup entry.
- Preserved the read-only client, five-minute refresh, stale handling and existing plugin identity/workflows.
- Fixed Windows startup-script encoding with UTF-16; installed preferences are anchored to the app location.
- Added resize/startup tests, current screenshots and updated privacy/install guidance.

Known limits: 3:2 sizing from 360–960 pixels wide; Python/Tk and signed-in Codex executable required. Full reboot/sign-out, other DPI/monitors, screen readers and extended unattended use remain unverified.

## 0.3.0 — 2026-10-06

First public beta under Krēˈādiv Worx, with an MIT license.

- Added the local Codex skill, sanitized status helper, Windows launch helper and marketplace manifests.
- Packaged the existing compact rounded usage card: teal progress bars, one/two available plan windows, five-minute refresh, stale-state handling, pin and position preferences.
- Replaced private-only setup messages with public Python/Tk requirements.
- Added privacy documentation, release packaging, plugin-boundary checks and Windows CI.

Known limitations: Python/Tk and a signed-in Codex executable are required; npm shims are unsupported. Experimental app-server protocol. Other DPI/monitor configurations, accessibility, sleep/resume and long-run behavior need more testing. No iOS/lock-screen or Windows Widgets board integration. See docs/VERIFICATION.md for observed tests.

## 0.2.0 — 2026-10-06 (private prototype)

Compact borderless card, native rounded region, 96% opacity, teal bars and per-window reset countdowns. Preserved live read-only usage and preferences.
