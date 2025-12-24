# AI Bot Author Detection - Tasks

**Last Updated: 2025-12-24**

## Phase 1: Add Author Detection Function (S effort) ✅

- [x] Add `detect_ai_author()` to `ai_detector.py` (reuse `detect_ai_reviewer`)
- [x] Add unit tests for `detect_ai_author()`
- [x] Test detection of known bots: devin-ai-integration[bot], coderabbitai, etc.

## Phase 2: Integrate in GraphQL Sync (M effort) ✅

### 2.1 Update `_process_pr()` in `github_graphql_sync.py`
- [x] Import `detect_ai_in_text` and `detect_ai_author` from ai_detector
- [x] Check if author_login is a bot using `detect_ai_author(author_login)`
- [x] Run `detect_ai_in_text()` on PR title + body
- [x] Combine results to set `is_ai_assisted` and `ai_tools_detected`
- [x] Add to `pr_defaults` dict before creating PR

### 2.2 Update `_process_pr_incremental()`
- [x] Same changes as above for incremental sync

### 2.3 Unit Tests
- [x] Test PR by bot author gets `is_ai_assisted=True`
- [x] Test PR with AI disclosure in body gets `is_ai_assisted=True`
- [x] Test PR with neither stays `is_ai_assisted=False`
- [x] Test `ai_tools_detected` populated correctly

## Phase 3: Handle Bot Authors in TeamMember (S effort) - SKIPPED

- [x] Decided not to add `is_bot` BooleanField - using `ai_tools_detected` instead
- [x] Added `AI_TOOL_DISPLAY_NAMES` mapping for friendly names
- [x] Bot authors without TeamMember show friendly name directly from ai_tools_detected

## Phase 4: UI Display (S effort) ✅

### 4.1 PR Table Updates
- [x] Show bot badge next to bot authors in table.html
- [x] Use friendly name from AI_TOOL_DISPLAY_NAMES (e.g., "Devin AI")

### 4.2 Template Helper
- [x] Add `ai_tools_display` filter for bot author display
- [x] Handle case where author is None but we know it's a bot

## Phase 5: Testing (M effort) ✅

### Unit Tests
- [x] Test `detect_ai_author()` with various bot usernames (10 tests)
- [x] Test GraphQL sync creates AI-assisted PR for bot author (8 tests)
- [x] Test GraphQL sync sets `ai_tools_detected` from body

### E2E Tests
- [ ] Test bot-authored PR shows with bot badge in UI (deferred)
- [ ] Test AI filter includes bot-authored PRs (deferred)

## Acceptance Criteria

1. **Bot Detection** ✅
   - PRs by `devin-ai-integration[bot]` marked as AI-assisted
   - PRs by `coderabbitai` marked as AI-assisted
   - `ai_tools_detected` includes bot type (e.g., ["devin"])

2. **Text Detection** ✅
   - PRs with "AI Disclosure" in body still detected
   - Both bot author AND text detection work together

3. **UI Display** ✅
   - Bot authors show friendly name (e.g., "Devin AI")
   - Bot badge visible in PR table when author is None
   - AI column tooltip shows friendly names

## Files Modified

| File | Changes |
|------|---------|
| `apps/metrics/services/ai_detector.py` | Added `detect_ai_author()` function |
| `apps/metrics/services/ai_patterns.py` | Added `AI_TOOL_DISPLAY_NAMES` and `get_ai_tool_display_name()` |
| `apps/integrations/services/github_graphql_sync.py` | Apply AI detection in sync |
| `apps/metrics/tests/test_ai_detector.py` | Added 10 author detection tests |
| `apps/integrations/tests/test_github_graphql_sync.py` | Added 8 AI detection tests |
| `apps/metrics/templatetags/pr_list_tags.py` | Added `ai_tools_display` filter |
| `templates/metrics/pull_requests/partials/table.html` | Bot display with badge |

## Test Results

- 48 AI detector tests passing
- 56 GraphQL sync tests passing (including 8 new AI detection tests)
- 34 PR list view tests passing
