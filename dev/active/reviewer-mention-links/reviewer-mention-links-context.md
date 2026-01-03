# Reviewer @Mention Links - Context

**Last Updated**: 2026-01-02

## Key Files

### Core Implementation

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/metrics/services/pr_list_service.py:138-154` | PR filtering logic | Add `reviewer_name` filter parallel to `github_name` |
| `apps/metrics/views/pr_list_views.py:43-59` | Filter key extraction | Add `"reviewer_name"` to filter_keys list |
| `apps/metrics/templatetags/pr_list_tags.py:898-936` | `linkify_mentions` filter | Add `@@username` pattern support |

### Prompt Templates

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/metrics/services/insight_llm.py:100-160` | System prompt | Add `@@` documentation and examples |
| `apps/metrics/prompts/templates/insight/user.jinja2:39-41` | Bottleneck data | Change `@` to `@@` for bottleneck |

### Test Files

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/metrics/tests/test_pr_list_service.py:64-114` | github_name tests | Add parallel reviewer_name tests |
| `apps/metrics/tests/test_pr_list_tags.py:625-698` | linkify_mentions tests | Add @@ syntax tests |

## Current Implementation

### Existing github_name Filter (pr_list_service.py:142-154)

```python
# Filter by author GitHub username (e.g., "@johndoe" or "johndoe")
# Security: Only matches team members within the specified team
github_name = filters.get("github_name")
if github_name:
    # Strip @ prefix if present
    username = github_name.lstrip("@")
    # Look up team member by github_username within team (team-scoped = secure)
    try:
        member = TeamMember.objects.get(team=team, github_username__iexact=username)
        qs = qs.filter(author=member)
    except TeamMember.DoesNotExist:
        # No matching team member - return empty queryset
        qs = qs.none()
```

### Existing linkify_mentions Filter (pr_list_tags.py:902-936)

```python
# Pattern to match @username mentions (alphanumeric and hyphens, like GitHub usernames)
# Uses negative lookbehind to avoid matching emails like user@example.com
MENTION_PATTERN = re.compile(r"(?<![a-zA-Z0-9])@([a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)")

@register.filter
def linkify_mentions(text: str | None, days: int = 30) -> str:
    # ... escapes text first for XSS protection
    def replace_mention(match):
        username = match.group(1)
        url = f"/app/pull-requests/?github_name=@{username}&days={days}"
        return (
            f'<a href="{url}" target="_blank" rel="noopener" '
            f'class="text-primary hover:underline font-medium">@{username}</a>'
        )
    result = MENTION_PATTERN.sub(replace_mention, escaped_text)
    return mark_safe(result)
```

### Current Bottleneck in User Prompt (user.jinja2:39-41)

```jinja2
{% if team_health.bottleneck %}
- ⚠️ BOTTLENECK: @{{ team_health.bottleneck.github_username }} ({{ team_health.bottleneck.reviewer_name }}) has {{ team_health.bottleneck.pending_count }} pending reviews
{% endif %}
```

## Design Decisions

### Decision 1: Dual Syntax (@@ for reviewers)

**Chosen:** Use `@@username` for reviewer mentions, `@username` for authors

**Alternatives Considered:**
1. **Semantic analysis** - Detect "pending reviews" in text → Rejected: fragile, complex
2. **Separate fields** - `reviewer_mentions` field in insight → Rejected: schema change, LLM complexity
3. **URL parameter in text** - `@username[reviewer]` → Rejected: ugly in display

**Rationale:** Simple regex, no breaking changes, explicit intent

### Decision 2: Process @@ Before @

**Chosen:** Match `@@` pattern first, then `@` pattern

**Rationale:** Prevents `@@alice` being matched as `@` + `@alice`. Order matters.

### Decision 3: Display @@ as Single @

**Chosen:** `@@alice` displays as `@alice` in rendered HTML

**Rationale:** Users don't need to see the internal syntax distinction

## Test Patterns

### Pattern: Parallel Test Structure

For each `github_name` test, create corresponding `reviewer_name` test:

```python
# Existing
def test_filter_by_github_name(self): ...
def test_filter_by_github_name_case_insensitive(self): ...
def test_filter_by_github_name_not_found_returns_empty(self): ...
def test_filter_by_github_name_team_scoped(self): ...

# New (parallel structure)
def test_filter_by_reviewer_name(self): ...
def test_filter_by_reviewer_name_case_insensitive(self): ...
def test_filter_by_reviewer_name_not_found_returns_empty(self): ...
def test_filter_by_reviewer_name_team_scoped(self): ...
```

### Pattern: Factory Setup

```python
# Create member with known github_username
member = TeamMemberFactory(team=self.team, github_username="alice-dev")
# Create PR with that member as author (for github_name tests)
pr = PullRequestFactory(team=self.team, author=member)
# Create PR with review from that member (for reviewer_name tests)
pr = PullRequestFactory(team=self.team, author=self.other_member)
PRReviewFactory(team=self.team, pull_request=pr, reviewer=member)
```

## Dependencies

### Models Used

- `TeamMember` - Has `github_username` field for lookup
- `PullRequest` - Has `author` FK to TeamMember
- `PRReview` - Has `reviewer` FK to TeamMember, `pull_request` FK

### Existing Filters Referenced

- `reviewer` filter (by ID) already exists at line 159-167
- Can reuse similar PRReview query pattern

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| `@@@alice` | Match as `@@` + `@alice` (two mentions) |
| `@@` alone | No match (needs username) |
| `user@@example.com` | No match (not at word boundary) |
| `@@alice-dev` | Valid match (hyphenated username) |
| `@@123` | No match (must start with letter) |

## Related Work

### Previous Commit (7405706)

Added initial `@username` → author linking:
- `linkify_mentions` filter
- `github_name` filter
- Tests for both

### Reverted Commit (81fde00)

Original implementation had similar features but was reverted due to "number leaks" in LLM output. Current approach keeps qualitative language while adding linking.
