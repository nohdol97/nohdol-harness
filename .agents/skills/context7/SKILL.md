---
name: context7
description: Fetch current, version-specific documentation for libraries, frameworks, SDKs, APIs, and CLI tools via the context7 MCP (resolve-library-id then query-docs) instead of answering library API questions from memory. Use when the user asks how to use, configure, install, migrate, or debug a specific library or framework - React, Next.js, Prisma, Tailwind, Django, Spring Boot, etc. Do NOT use for - Anthropic/Claude/LLM/model-id/pricing questions (→ claude-api built-in skill), reading one specific user-given URL (→ defuddle/WebFetch), or general programming concepts and business-logic debugging. When context7 is unavailable, fall back to WebFetch/WebSearch. Re-run keywords - context7, library docs, framework docs, API reference, 라이브러리 문서, 프레임워크 사용법, 라이브러리 사용법, 문서 조회.
---

# context7 — Fetch Current Library Documentation (Docs over Memory)

## Why This Skill

Libraries and frameworks change their APIs with every version. When the model answers from training-time memory, it confidently gets it wrong — **deprecated signatures, removed options, changed configuration**. The `context7` MCP fetches **current documentation, curated and indexed per version**, in real time, eliminating those wrong answers.

The problem is not capability but **activation timing**. MCP tools just sit there; they only get called when the model itself thinks "I should use this now" — so even a useful tool goes silently unused if the model simply answers from memory. This skill is that activation layer: it pins down the trigger as **"when asked about library usage, configuration, migration, or library-specific errors, query context7 first instead of answering from memory"** (the same pattern the Claude Code built-in `claude-api` skill applies to Anthropic docs).

However, this is an **external MCP dependency**. If it is missing or fails, **always fall back to WebFetch/WebSearch** — a user question must never be blocked by tool absence (the same thin-wrapper approach as the defuddle skill).

## Procedure

1. **Check negative triggers first** (the `Do NOT use for` in the description):
   - **Anthropic/Claude/LLM, model-ID, or pricing** questions → go to the **`claude-api` skill (Claude Code built-in)**, not this skill (context7 is for third-party libraries).
   - **Reading a specific user-given URL** → go to **`defuddle`/WebFetch** (context7 is a library index, not a URL reader).
   - **General programming concepts / business-logic debugging** → judge directly without tools (not a documentation-lookup target).

2. **Check the dependency**: see whether the context7 MCP tool (`mcp__context7__resolve-library-id`) is present in this session.
   - Present → step 3.
   - Absent → ask the user once and guide installation (`claude mcp add context7 --scope user -- npx -y @upstash/context7-mcp`; global registration takes effect from the next session), or if declined/impossible, **fall back to WebFetch/WebSearch immediately**. **Never install without permission.** (To make it permanent, follow harness-install step 3c — it is guided automatically on new installations.)

3. **Resolve the library ID**: convert the library name (e.g. "next.js", "prisma") to a context7 ID with `mcp__context7__resolve-library-id`. If there are multiple candidates, pick the one that **matches the library the user named most exactly** (official name, recognition, version match). If ambiguous, confirm with the user which one — scraping the wrong library's docs is worse than answering from memory.

4. **Query the docs**: pass the resolved ID and a **specific topic** (e.g. "app router middleware", "prisma migrate deploy") to `mcp__context7__query-docs` and fetch only the needed sections. If the version matters (migration or version-specific questions), specify the version as well.

5. **Use the result**: answer grounded in the fetched docs. Quote code, signatures, and config values **verbatim** (translating them breaks reproducibility — root AGENTS.md §15 guard 2). Do not fill gaps in the docs from memory; if something is missing, say so and supplement with WebFetch/WebSearch.

## Fallback Rule (Fixed)

Every failure path of this skill **converges to WebFetch/WebSearch**: MCP not installed, installation declined, ID resolution failure, empty query result, connection error. Fallback is a normal path, not a failure — context7 is only an **accuracy/token-optimization means** for documentation lookup, not the sole channel to documentation. Complete the answer by reading the official docs URL directly with WebFetch.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Accuracy | Memory-based answers → confidently wrong about deprecated APIs and changed configs | Answers grounded in current per-version docs |
| Activation rate | Even with the context7 MCP loaded, the model does not think of it and it goes silently unused | Trigger states "query instead of memory" → higher activation |
| Robustness | (n/a) | On absence/failure, auto-converges to WebFetch/WebSearch — the capability never dies |
| Boundaries | Trigger collisions with claude-api and defuddle | Routing settled by negative triggers |
