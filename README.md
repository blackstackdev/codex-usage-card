# Usage Card for Codex

A little room for your limits. A compact Windows desktop card by **Krēˈādiv Worx**, with a local Codex skill plugin. MIT open source. Version 0.3.0, 6 October 2026 — public beta.

Rounded dark card, teal progress bars, remaining percentages and reset countdowns. Drag it into place, pin it above your work, or refresh on demand. The card refreshes every five minutes and shows only the plan windows your account exposes. A failed refresh keeps the previous reading visibly stale.

## Desktop download

Download **Usage-Card-for-Codex-v0.3.0-windows.zip** from the [release page](https://github.com/blackstackdev/codex-usage-card/releases/tag/v0.3.0), extract it, then double-click **Launch Widget.vbs**. If Windows blocks script launching, run `python widget.py` from that folder.

Requires Windows, **Python 3.11+ with Tcl/Tk**, `pythonw.exe` on PATH for the double-click launcher, and a locally signed-in **Codex CLI executable**. The Codex desktop app's bundled `codex.exe` is detected automatically; a `codex.exe` on PATH also works. npm `.cmd` shims are not currently supported. No third-party Python packages are needed. This is a script download, not a bundled executable or installer.

**Close** or Escape exits. **Pin** keeps it above other windows. **Menu** includes exact reset dates and About. Drag the header or background to move it. There is no conventional taskbar/minimize entry; relaunch with the same file. One instance runs per Windows session.

## Codex plugin

The plugin supplies a local skill for **“Show my Codex plan limits”** and **“Open my Codex usage card.”** It executes the bundled Python helper on your computer. It has no MCP server or cloud service.

Using Codex CLI 0.160.1 or another version with `plugin marketplace` support:

```powershell
codex plugin marketplace add blackstackdev/codex-usage-card --ref v0.3.0
codex plugin add codex-usage-card@kreadiv-usage-card
```

Open a new Codex chat and select **Usage Card for Codex** from the plugins picker, then ask for either workflow. If the installed CLI is not on PATH, use the full path to your `codex.exe` for these commands.

The **codex-usage-card-v0.3.0-plugin.zip** asset also contains the self-contained plugin for hosts accepting local plugin packages. GitHub marketplace installation uses this repository's `.agents/plugins/marketplace.json`.

## Data and limitations

The card starts a short-lived installed Codex app-server, reads `account/rateLimits/read`, then closes it. Codex handles the existing sign-in and server request. The card does not read authentication files or run a model turn. Only position and pin settings are saved at `%LOCALAPPDATA%\kreadiv-worx\CodexUsageWidget\settings.json`. No startup tasks, new account connections or credit resets are created. [Privacy details](PRIVACY.md).

Limits are server snapshots shared across the account. The CLI account may differ from the desktop account after switching accounts. The app-server protocol is experimental and may change. Windows desktop only; subtle translucency, without a blurred backdrop. Independent of OpenAI.

Tested on one Windows PC with Python 3.11.9 / Tk 8.6 / Codex CLI 0.160.1, including execution from an extracted folder with spaces. Automated checks cover data, protocol, error handling and native Tk construction. Other DPI/monitor arrangements, screen readers, sleep/resume and long unattended use remain unverified. See [verification](docs/VERIFICATION.md) for the exact evidence and plugin-host verification scope.

## Development

```powershell
python -m unittest discover -s plugins/codex-usage-card/app/tests -v
python -m unittest discover -s tests -v
python plugins/codex-usage-card/app/widget.py --smoke
python plugins/codex-usage-card/scripts/usage.py status
```

Report problems in [GitHub Issues](https://github.com/blackstackdev/codex-usage-card/issues). Remove personal details before sharing logs. [Changelog](CHANGELOG.md) · [MIT license](LICENSE).
