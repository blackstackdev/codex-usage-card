from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-usage-card"
version = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))["version"]
dist = ROOT / "dist"
dist.mkdir(exist_ok=True)

def package(name, sources):
    destination = dist / name
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, prefix in sources:
            paths = sorted(source.rglob("*")) if source.is_dir() else [source]
            for path in paths:
                if not path.is_file() or "__pycache__" in path.parts or path.suffix in (".pyc", ".tmp"):
                    continue
                relative = path.relative_to(source) if source.is_dir() else Path(source.name)
                archive.write(path, str(Path(prefix) / relative))
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".sha256").write_text(digest + "  " + name + "\n", encoding="ascii")
    print(json.dumps({"file": name, "sha256": digest, "bytes": destination.stat().st_size}))

package(f"codex-usage-card-v{version}-plugin.zip", [(PLUGIN, "codex-usage-card")])
package(f"Usage-Card-for-Codex-v{version}-windows.zip", [
    (PLUGIN / "app", f"Usage-Card-for-Codex-v{version}"),
    (ROOT / "README.md", f"Usage-Card-for-Codex-v{version}"),
    (ROOT / "LICENSE", f"Usage-Card-for-Codex-v{version}"),
    (ROOT / "PRIVACY.md", f"Usage-Card-for-Codex-v{version}"),
    (ROOT / "CHANGELOG.md", f"Usage-Card-for-Codex-v{version}"),
    (ROOT / "docs", f"Usage-Card-for-Codex-v{version}/docs")])
