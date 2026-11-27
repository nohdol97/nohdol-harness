#!/usr/bin/env python3
"""Print the §8 lesson index for runtimes that do not load it themselves (Pi).

Usage: memory-index.py [--root <harness root>]

Claude Code loads ~/.claude/projects/<slug>/memory/MEMORY.md on its own; root
AGENTS.md §8 makes that directory the shared lesson store. The slug is the root
path with every character outside [A-Za-z0-9] replaced by "-", the rule Claude
Code uses for its project directories (e.g. C:\\Users\\a\\h -> C--Users-a-h).
CLAUDE_CONFIG_DIR replaces ~/.claude as it does for Claude Code.

Prints the index path then the index, or nothing when there is no index. Always
exits 0 so a session start never fails on a missing store.
"""
import os
import re
import sys


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def main(argv):
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    if argv[:1] == ["--root"] and len(argv) == 2:
        root = os.path.abspath(argv[1])
    elif argv:
        print(__doc__, file=sys.stderr)
        return 0
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    index = os.path.join(config, "projects", slug(root), "memory", "MEMORY.md")
    try:
        with open(index, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return 0
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"§8 lesson index: {index}")
    print(text, end="" if text.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
