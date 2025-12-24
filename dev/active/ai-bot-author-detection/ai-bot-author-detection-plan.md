# AI Bot Author Detection - Implementation Plan

**Last Updated: 2025-12-24**

## Executive Summary

Enhance AI detection to identify PRs authored by AI bots (Devin, Claude, Cursor bots, etc.) and display bot authors correctly in the UI. Currently, the system detects AI usage via PR body text and commit co-authors, but doesn't recognize when the PR author itself is an AI bot.

## Current State Analysis

### What Works
1. **AI Text Detection** (`apps/metrics/services/ai_detector.py`)
   - `detect_ai_in_text()` - Finds AI signatures in PR body/title
   - Patterns defined in `ai_patterns.py` for Claude, Copilot, Cursor, Devin, etc.

2. **AI Reviewer Detection** (`apps/metrics/services/ai_patterns.py`)
   - `AI_REVIEWER_BOTS` dict maps usernames to AI types
   - Includes `devin-ai-integration[bot]`, `coderabbitai`, etc.
   - Used by `detect_ai_reviewer()` function

3. **AI Co-Author Detection** (`apps/integrations/services/ai_detection.py`)
   - `detect_ai_coauthor()` - Finds AI in commit messages
   - Separate patterns list (legacy, should consolidate)

### What's Missing
1. **Bot Author Detection** - No `detect_ai_author()` function
2. **Sync Integration** - GraphQL sync doesn't apply AI detection
3. **UI Display** - Bot authors display as "Unknown" or missing

### Key Files
- `apps/metrics/services/ai_patterns.py` - Pattern registry (has `AI_REVIEWER_BOTS`)
- `apps/metrics/services/ai_detector.py` - Detection functions
- `apps/integrations/services/github_graphql_sync.py` - PR sync logic
- `apps/metrics/processors.py` - Webhook processing

## Proposed Future State

### Phase 1: Add Author Detection Function
Reuse `AI_REVIEWER_BOTS` patterns for author detection since bot usernames are the same whether they're reviewing or authoring.

### Phase 2: Apply Detection During Sync
When syncing PRs, check if author username is a bot and set `is_ai_assisted=True`.

### Phase 3: Display Bot Authors in UI
Show "Devin AI" or similar instead of raw bot username.

## Implementation Phases

### Phase 1: Add `detect_ai_author()` Function (S effort)

Add to `apps/metrics/services/ai_detector.py`:
```python
def detect_ai_author(username: str | None) -> AIReviewerResult:
    """Detect if a PR author is an AI bot (same logic as reviewer detection)."""
    return detect_ai_reviewer(username)  # Reuse existing function
```

### Phase 2: Integrate Detection in GraphQL Sync (M effort)

Modify `apps/integrations/services/github_graphql_sync.py`:
- In `_process_pr()` function, after getting author:
  1. Check if author_login is an AI bot
  2. Also run `detect_ai_in_text()` on body
  3. Set `is_ai_assisted` and `ai_tools_detected` on PR

### Phase 3: Create Virtual TeamMember for Bots (S effort)

When a bot authors a PR:
- Create/get a TeamMember with `is_bot=True` flag (or use display_name like "Devin AI")
- Store bot type in TeamMember model

### Phase 4: UI Display (S effort)

In PR table template:
- Show bot icon/badge next to bot authors
- Display friendly name (e.g., "Devin AI") instead of "devin-ai-integration[bot]"

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Bot usernames change | Low | Pattern-based matching handles variations |
| False positives | Low | Bot usernames are distinctive (contain [bot]) |
| Missing bots | Low | Easy to add new patterns |

## Success Metrics

1. All PRs by known bots marked as `is_ai_assisted=True`
2. Bot authors displayed with friendly names in UI
3. AI adoption metrics accurately reflect bot-authored PRs
