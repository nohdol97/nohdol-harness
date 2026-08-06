# Product-code design reference (read on demand)

Two design-time aids for sub-project product code. Both are **reference, not obligation** — root §16 remains the rule, and nothing here mandates a step. Ported from mattpocock/skills (`codebase-design`, `prototype`); adoption rationale in `docs/proposals/2026-08-07-mattpocock-skills-review.md`.

Root §16 tells you to climb *away* from writing code (necessity → reuse → stdlib → platform → dependency → one line → minimal implementation). It says nothing about the shape of what you do write. That is what §1 supplies. §2 covers the other gap: a design question that no amount of climbing settles, because the answer is only visible once something runs.

## 1. Deep modules — vocabulary for interface shape

Design **deep modules**: a lot of behaviour behind a small interface, at a clean seam, testable through that interface. Use these words exactly; consistent naming is most of the value.

- **Module** — anything with an interface and an implementation, at any scale (function, class, package, tier-spanning slice). Prefer it over "component", "service", "unit".
- **Interface** — everything a caller must know to use the module correctly: not just the type signature but invariants, ordering constraints, error modes, required configuration, and performance characteristics. "API" and "signature" are narrower and mislead here.
- **Seam** — the place where behaviour can be altered without editing in that place; the *location* of a module's interface. Where the seam goes is its own decision, separate from what sits behind it. Prefer it over "boundary".
- **Adapter** — a concrete thing satisfying an interface at a seam. Names a role, not a substance: a small adapter can have a large implementation (a Postgres repository) and a large adapter a small one (an in-memory fake).
- **Depth** — leverage at the interface: how much behaviour a caller or a test can exercise per unit of interface it must learn. **Deep** = large behaviour behind a small interface; **shallow** = the interface is nearly as complex as the implementation. Depth is *not* the ratio of implementation lines to interface lines — that framing rewards padding the implementation.

Three checks worth running while designing:

- **The deletion test.** Imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep. (This is §16's necessity question asked about a module rather than a line.)
- **The interface is the test surface.** Callers and tests cross the same seam. Wanting to test *past* the interface is evidence the module is the wrong shape — and note that §16 does not license dropping the test, so the shape is what changes.
- **One adapter is a hypothetical seam; two are a real one.** Do not introduce a seam until something actually varies across it — the same judgment §16 makes about speculative abstraction, stated in seam terms.

Depth is a property of the **interface**, not the implementation: a deep module may be internally composed of small swappable parts, with internal seams its own tests use, as long as none of that reaches the caller.

## 2. Throwaway prototype — an allowed way to answer a design question

§13-1 requires a spec before implementation. A prototype is not a substitute for that spec — it is a way to *get* the answer the spec needs, when the question is "does this state model / this shape actually work" and reasoning on paper is not settling it. **Where the prototype's own commit lands under §13 is not this file's call**: those clauses own their scope, so put the situation to the user rather than reading an exemption into it here.

Permitted, under all of these:

1. **Throwaway from the first line, and labelled as such.** Put it next to the module it is probing so the context is obvious, and name it so no reader mistakes it for production.
2. **Trivial to run** — one command from the project's existing task runner, or a single file the user opens. No setup thinking.
3. **No persistence, no polish.** State in memory; no tests, no error handling beyond what makes it run, no abstractions. Persistence is usually the thing being checked, not a dependency to take on.
4. **Surface the state** after every action, so what changed is visible rather than inferred.
5. **The main branch keeps only the validated decision.** Fold the answer into the real work, and keep the prototype itself on its own branch with a pointer to it from the spec or tracking issue. **How that branch is created, based, and cleaned up is `branch-workflow`'s axis, not this file's** — follow it, including its profile split (worktree off `origin/main`; no worktree on a `사내` profile, ADR 043). A prototype carries no tests by design, so its commit meets `tdd-gate` like any other. **This file does not classify it** — §13-4 scopes `[no-test]` to behavior-invariant changes and is the only place that may widen that class, so put the situation to the user and let §13-4 decide rather than asserting an exemption here.
6. **Record the verdict, not just the artifact** — the question it settled and the answer — where the spec or the issue will be read. A prototype whose conclusion lives only in the branch has answered nothing durable.

When the question is not a design question — a bug, a regression, "why does this fail" — this is the wrong tool: that is `troubleshooter`, which needs a reproduction rather than a probe.
