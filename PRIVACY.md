# Privacy

Version 0.3.0 — 6 October 2026

Usage Card for Codex runs locally. It asks the installed Codex CLI's app-server to read the existing signed-in account's plan limits over local standard input/output. The CLI makes its own request to OpenAI; its privacy policy and authentication behavior still apply. Usage Card does not open credential files, request a new sign-in, collect account identity, redeem reset credits or run model turns.

Remaining percentage, window length and reset time stay in memory. The status helper prints those fields and an observation timestamp to the invoking Codex chat. The host's handling of chat/tool output applies. Failed server responses are not printed raw.

Only x/y window position and pin preference are written to `%LOCALAPPDATA%\kreadiv-worx\CodexUsageWidget\settings.json`. Delete that file to reset preferences. Closing the widget stops its refreshes and cleans up an in-flight app-server. Removing the plugin and downloaded files uninstalls the software; saved preferences can be removed separately.

The product has no telemetry, hosted backend, local HTTP server or analytics SDK. Its app-server request disables analytics. There is no automatic startup registration. GitHub itself handles download and issue traffic under GitHub's policies. Do not include credentials or personal information in public issues.
