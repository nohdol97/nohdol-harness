# Orchestration pattern selection guide

## Flowchart — choose by the shape of the problem

```
What shape is the problem?
├─ Are the steps sequentially dependent? (earlier output feeds later input) → 1. Pipeline
├─ Must the same input be viewed from several angles at once?               → 2. Fan-out/fan-in
├─ Must input be classified and sent to one matching expert?                → 3. Expert pool
├─ Must a separate agent guarantee deliverable quality?                     → 4. Generate-verify
├─ Does work arise and get distributed dynamically at runtime?              → 5. Supervisor
└─ Does the problem split into sub-domains? (one team cannot cover it)      → 6. Hierarchical delegation
```

Always start with the simplest pattern. Transition only when the signal table below points to it — a heavyweight pattern without a transition signal adds latency and cost with no quality gain.

## Transition-signal table

| Current pattern | Transition signal | Next pattern |
|---|---|---|
| Single agent | Context explosion, frequent session breaks | Pipeline |
| Pipeline | Time wasted processing independent work sequentially | Fan-out/fan-in |
| Fan-out/fan-in | Different expertise needed per task, same role hits its limit | Expert pool |
| Expert pool | Deliverable quality variance, no verification | Generate-verify |
| Generate-verify | Real-time coordination between agents needed, dynamic task allocation | Supervisor |
| Supervisor | Single supervisor exceeds 5–10 members, domain decomposes into sub-teams | Hierarchical delegation |

## Pattern essentials

### 1. Pipeline — order creates meaning

Each stage receives the previous stage's deliverable as a `_workspace/` file. Use **only when it is the only logically possible order** — putting order-swappable work into a pipeline just wastes time.

e.g. spec-drafter → api-designer → schema-migrator / CI·CD's lint → build → test → deploy

### 2. Fan-out/fan-in — same input, different angles (classic distribution)

**Real-time cross-verification** between members must be possible, so SendMessage matters (a security member's finding can change a performance member's judgment). Fan-out dispatch must be **simultaneous in one turn** (orchestrate B-mode simultaneous-dispatch convention) — calling and waiting one by one degenerates into serial.

e.g. same diff → parallel security/performance/test/style reviews → integration

### 3. Expert pool — router + experts

Fan-out has **all** N members working, but the expert pool has **only one** of N working. Therefore **the router's classification accuracy is critical** — misclassify and the wrong expert gives the wrong answer.

e.g. bug-report routing — UI bugs to ui-bug-specialist, data issues to data-bug-specialist

### 4. Generate-verify — make, inspect, remake

One agent produces the deliverable and a **different** agent verifies it (self-verification passes self-bias). Default retries 2–3; at the limit, request human judgment. Use when deliverable quality assurance matters.

e.g. TDD automation — code-generator + test-runner

### 5. Supervisor — runtime dynamic distribution

The supervisor manages the task queue; workers read the TaskCreate queue and claim tasks themselves ("I'll take this one"). The supervisor adjusts dynamically while watching progress. **3–5 workers is optimal** — beyond that the supervisor becomes the bottleneck.

### 6. Hierarchical delegation — director → team leads → workers

When the problem is too large or complex for one team, split by domain and hand to sub-teams (fan-out plus one level of depth). The director sees only the leads' outputs; leads see only the workers' outputs — reporting that skips a layer collapses the structure.

**Never exceed 2 levels of depth** — latency grows exponentially.

e.g. a PM hands "add payment feature" to frontend/backend leads, each directing 3 workers

## Composite patterns — hybrid composition rules

Real harnesses use a different pattern per Phase. Combine per these rules:

1. **Phase decomposition first**: Map the work onto the standard skeleton `collect → design/consensus → implement → independent verify → integrate` (orchestrate C-mode table) and drop unneeded Phases — but **keep the order**, and if implementation is included, the verification Phase cannot be skipped (orchestrate mandatory-verification rule).
2. **Independent judgment per Phase**: Choose each Phase's pattern separately from the flowchart above by that Phase's problem shape. Forcing one pattern on the whole job guarantees some Phase wears clothes that do not fit.
3. **Mode mapping**: Phases needing inter-member communication (consensus, cross-verification, dynamic distribution) = agent team; independent parallel Phases (collection, isolated verification) = subagents. The verifier defaults to **separation from the implementation team (subagent)** — isolation is independence.
4. **Boundaries are `_workspace/` files**: Pass inter-Phase data only via `phase{N}_{agent}_{content}.md`, and state the execution mode at the top of each Phase (orchestrate hybrid-mode convention). Passing via memory makes Phase re-runs and debugging impossible.
5. **Get heavier only on transition signals**: Start from the skeleton, and promote a Phase's internal pattern only when the transition-signal table above points to it.

e.g. "payment module refactoring" → ① collect (3 fan-out subagents: code structure, test status, dependencies) → ③ implement (implementer pipeline: spec → tests → implementation) → ④ verify (reviewer subagent — against spec completion criteria) → ⑤ integrate (integrator). No design disputes, so ② is skipped.
