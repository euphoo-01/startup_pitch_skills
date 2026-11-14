#!/usr/bin/env python3
"""Install the two portable agent skills into one or more agent skill directories."""
import argparse
import shutil
from pathlib import Path

TARGETS = {"codex": ".agents/skills", "cursor": ".agents/skills", "claude": ".claude/skills"}
USER_TARGETS = {"codex": ".agents/skills", "cursor": ".agents/skills", "claude": ".claude/skills"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", choices=[*TARGETS, "all"], default="codex")
    p.add_argument("--scope", choices=["project", "user"], default="project")
    p.add_argument("--project", type=Path, default=Path.cwd(), help="project root for project installs")
    p.add_argument("--force", action="store_true", help="overwrite installed skills")
    args = p.parse_args()
    root = Path(__file__).resolve().parent
    installed_locations = set()
    for tool in ([*TARGETS] if args.target == "all" else [args.target]):
        prefix = Path.home() if args.scope == "user" else args.project.resolve()
        destination = prefix / (USER_TARGETS[tool] if args.scope == "user" else TARGETS[tool])
        if destination in installed_locations:
            continue
        installed_locations.add(destination)
        for src in sorted((root / "skills").iterdir()):
            dst = destination / src.name
            if dst.exists():
                if not args.force:
                    raise SystemExit(f"Already installed: {dst}. Use --force to replace.")
                shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)
            print(f"Installed {src.name} for {tool}: {dst}")


if __name__ == "__main__":
    main()
