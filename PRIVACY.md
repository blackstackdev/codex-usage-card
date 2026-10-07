# Privacy

Version 0.4.0 — 7 October 2026.

Usage Card runs locally. It asks the installed Codex CLI app-server to read the existing account's plan limits over standard input/output. The CLI makes its own request to OpenAI; its authentication behavior and privacy policy apply. The card does not read auth files, collect account identity, request a new sign-in, redeem resets or run model turns.

Remaining percentage, duration and reset time stay in memory. The status helper prints those fields and an observation timestamp to the invoking chat; the host's handling of chat/tool output applies. Failed server responses are not printed raw.

Only x/y position, pin preference and width are saved in the local `kreadiv-worx\CodexUsageCosmic\settings.json`. Installed copies resolve settings next to their app folder, preserving the location across sign-in/manual launches. Older compact-card settings remain intact. Delete preferences to reset them. Closing the card stops refreshes and cancels an in-flight client request.

Startup is off by default. Enabling **Menu → Launch at Windows sign-in** installs a stable local app copy and writes a dedicated UTF-16 VBScript file in the current user's Startup folder. It references absolute paths to the installed Python and this app. Disabling removes only this utility's marked entry. No administrator service or scheduled task is created. Opening the card or requesting status does not register startup.

To uninstall: turn off startup, close the card, remove the installed app folder/download/plugin, and remove preferences separately if desired. Windows may expose the same startup entry through its Startup Apps settings; a Windows-disabled entry remains disabled until re-enabled there.

No telemetry, hosted backend, local HTTP service or analytics SDK. The app-server invocation disables analytics. GitHub handles download/issue traffic under its policies. Do not share credentials or personal information in public issues.
