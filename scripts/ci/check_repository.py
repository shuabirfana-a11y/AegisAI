"""Reject machine-local data in the tracked/index tree; never read secret values."""
import json
import subprocess
from pathlib import PurePosixPath, Path

ROOT = Path(__file__).resolve().parents[2]


def forbidden_paths(paths):
    rejected = []
    for name in paths:
        path = PurePosixPath(name.replace("\\", "/"))
        parts = path.parts
        local_dir = any(p in {".venv", "venv", "node_modules", "__pycache__",
                              ".pytest_cache", ".playwright-cli", ".worktrees"}
                        for p in parts)
        secret = (path.name == ".env" or
                  (path.name.startswith(".env.") and path.name != ".env.example"))
        local_file = path.suffix.lower() in {
            ".pem", ".key", ".pfx", ".p12", ".db", ".sqlite", ".sqlite3",
            ".dump", ".log", ".pid", ".pyc", ".pyo"
        }
        local_work = (parts and parts[0] in {"work", "outputs"}) and (
            path.as_posix() != "work/orchestration/baseline_hashes.json")
        if local_dir or secret or local_file or local_work:
            rejected.append(name)
    return rejected


def main():
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode("utf-8").rstrip("\0").split("\0")
    rejected = forbidden_paths(tracked)
    if rejected:
        print(json.dumps({"status": "FAIL", "forbidden_paths": rejected}))
        return 1
    print(json.dumps({"status": "PASS", "tracked_files": len(tracked),
                      "secret_values_read": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
