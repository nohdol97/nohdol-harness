#!/usr/bin/env python3
"""Run the shared permission guard with the writable workspace profile."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_readonly import main

if __name__ == '__main__':
    sys.exit(main(sandbox='workspace-write'))
