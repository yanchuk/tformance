# Layer 2: Epistemic Hierarchy in CLAUDE.md

**Date**: 2026-03-22
**Status**: Implemented
**Reference**: [Как заставить LLM не врать про версии](https://blognot.co/kak-zastavit-llm-ne-vrat-pro-versii/)

## Problem

LLMs don't distinguish trained knowledge from current reality. Simple instructions like "always verify versions" are too abstract — the model agrees and keeps hallucinating. Layer 1 (SessionStart hook) injects temporal context but doesn't set behavioral rules.

## Design

Three-layer epistemic honesty system, per the referenced article:

| Layer | Location | Responsibility |
|---|---|---|
| Layer 1 (Context) | `~/.claude/hooks/inject-temporal-context.sh` | Date, months gap, high-risk library list |
| **Layer 2 (Behavior)** | `CLAUDE.md` | Source hierarchy, verification, marking, anti-hallucination |
| Layer 3 (Web UI) | claude.ai preferences | Same principles for web interface |

### Layer 2 sections added to CLAUDE.md

1. **Epistemic Hierarchy** — strict source ranking: project files > external tools > training data ("Legacy Archive")
2. **Mandatory Verification** — trigger list for versions, APIs, deprecations, existence checks, LLM model names
3. **Response Marking** — `✓ VERIFIED (from [source])` / `⚠ FROM TRAINING (may be outdated)` / `? UNCERTAIN`
4. **Anti-Hallucination Rules** — deny-list: don't "correct" modern syntax, don't claim non-existence without checking, don't state versions from memory
5. **Version Handling** — 4-step protocol: check project files → use that version → ask user → trust user
6. **Permission to Say "I Don't Know"** — explicit encouragement to admit uncertainty over confident hallucination

### Hook cleanup

Removed behavioral rules from the hook (EPISTEMIC WARNING + MANDATORY VERIFICATION PROTOCOL blocks). Hook now emits only temporal context: date, gap, library list. Behavior lives exclusively in CLAUDE.md for higher persistence through compaction.

## Key principle

> Hook создаёт контекст, но не задаёт поведение. Поведение задаёт epistemic-правило в CLAUDE.md.

## Files changed

- `CLAUDE.md` — 6 new sections after "Critical Rules", before "Key Decisions"
- `~/.claude/hooks/inject-temporal-context.sh` — stripped to context-only
