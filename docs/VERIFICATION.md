# Verification scope

Version 0.3.0, 6 October 2026. Public beta.

Baseline: Windows, Python 3.11.9 / Tk 8.6 / Codex CLI 0.160.1.

Release-copy evidence on 6 October 2026:

- All eleven widget tests and four plugin-boundary tests passed.
- Native Tk smoke passed on the release source and both extracted release assets.
- Both ZIPs passed CRC, contained-path and private-data checks; hidden compatibility manifests are included.
- Plugin runtime ran successfully from an extracted directory containing spaces. A live status request returned the actual available Weekly window. No short window was fabricated.
- The open helper completed its single-instance path while the existing desktop card was running. A second new window was not expected. Fresh launch of the new version has not been visually verified.
- Codex CLI catalog discovery recognized `codex-usage-card@kreadiv-usage-card` version 0.3.0 through temporary configuration overrides. Existing marketplace configuration was preserved; the plugin was not installed into the author's host session.

The test suite covers invalid/missing values, percentage clamping, available plan windows, reset semantics, preference recovery, the exact read-only JSON-RPC sequence, error redaction and app-server cleanup. Plugin checks cover sanitized snapshots, unexpected-error redaction, invalid action rejection and synchronized manifests/assets. Native smoke covers one/two rows, short-first ordering, omitted rows, stale readings and pin persistence using temporary preferences.

Native automation is unavailable in the author's environment: no captured native screenshot, real pointer/keyboard acceptance or independent visual QA is claimed. Other Windows installations, DPI/monitor combinations, screen readers, sleep/resume and extended unattended operation remain unverified. A clean extracted folder on the same PC is not a fresh-PC acceptance test.

Catalog discovery, runtime invocation and skill selection in a new Codex host session are distinct. CLI marketplace discovery can validate manifests; fresh-session conversational skill execution remains a separate check unless explicitly recorded below.
