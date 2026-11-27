# Runtime: Pi Coding Agent

These instructions identify this runtime only when Pi loads this file into its system prompt. Reading or quoting the file in another CLI does not activate the exception.

Apply the Pi runtime exception in root AGENTS.md §11. Keep REGISTRY.md's installation profile unchanged. Root AGENTS.md remains the policy source; shared skills and roles remain under `.agents/`.

Pi does not load the root AGENTS.md §8 lesson store. At session start, before the first task, run `python3 .agents/hooks/memory-index.py` from the harness root (use `python` or `py` where `python3` is absent or fails, as the Windows Store alias does). Empty output means there are no lessons. Otherwise treat the printed index as the §8 lesson index: open a listed note only when its triggering situation matches the work at hand, never all notes. Record a new lesson as one file in that index's directory plus one index line naming the triggering situation, as Codex sessions do.
