# Survey Improvements Based on SO 2025 AI Insights

**Last Updated: 2025-12-22**

## Executive Summary

Enhance the PR survey system with **PR description-based voting** (not comments), **one-click voting**, and **AI auto-detection** to capture deeper insights about AI tool usage and developer trust. Informed by the Stack Overflow 2025 Developer Survey AI section findings, the goal is to enable correlating AI trust/accuracy perceptions with actual delivery metrics while maximizing response rates through frictionless voting.

### Key Findings from SO 2025 That Drive This Feature

| Metric | Value | Implication |
|--------|-------|-------------|
| AI tool usage | 84% (up from 76%) | Need to track WHICH tools specifically |
| Trust AI accuracy | Only 33% | Critical gap - majority are skeptical |
| Top frustration | "Almost right but not quite" (66%) | Need to quantify modification effort |
| Daily AI users | 51% | Frequency matters, not just yes/no |
| Agent usage emerging | 14% daily, 31% total | Track AI agents vs copilots |

### Business Value

1. **Correlation insights**: Connect trust levels with cycle time/review iterations
2. **Tool effectiveness**: Compare outcomes across different AI tools
3. **Hidden rework cost**: Quantify the "almost right" problem
4. **Trend tracking**: SO shows cooling enthusiasm (60% favorable, down from 70%+)
5. **Higher response rates**: One-click voting reduces friction significantly
6. **Auto-detection**: Skip surveys when AI usage is already evident from commits

---

## Current State Analysis

### Current Survey Model (`apps/metrics/models/surveys.py`)

**PRSurvey (Author Survey)**:
- `author_ai_assisted` - Boolean (null/True/False)
- `author_response_source` - CharField (github/slack/web) - **NEW**
- `ai_modification_effort` - CharField (none/minor/moderate/major/na) - **NEW**
- Single question: "Did you use AI assistance?"

**PRSurveyReview (Reviewer Survey)**:
- `quality_rating` - 1-3 scale (Could be better/OK/Super)
- `ai_guess` - Boolean guess
- `response_source` - CharField (github/slack/web) - **NEW**

### Current Delivery Channels

- **Slack only** - DM sent after PR merge
- No GitHub-native survey option
- Users must leave GitHub to respond

---

## Proposed Future State

### Multi-Channel Survey Delivery with AI Auto-Detection

```
┌─────────────────────────────────────────────────────────────────┐
│  PR Merged Event (GitHub Webhook)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Check for AI Co-Author Signatures                            │
│     - Scan commits for "Co-Authored-By: GitHub Copilot"          │
│     - Check for "Co-Authored-By: Claude", etc.                   │
│     - If found: Auto-mark as AI-assisted, skip author survey     │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│ AI Detected             │   │ No AI Detected          │
│ → Auto-mark survey      │   │ → Add voting to PR desc │
│ → Skip author question  │   │ → Schedule Slack fallback│
│ → Still ask reviewers   │   └─────────────────────────┘
└─────────────────────────┘
```

### PR Description Voting (Not Comments)

When PR is merged, append survey section to PR description:

```markdown
<!-- Original PR description content here -->

---

<!-- tformance-survey-start -->
## 🎉 tformance Survey

**Author @alice** - Was this PR AI-assisted?
→ [✅ Yes](https://app.tformance.com/survey/abc123/author?vote=yes) · [❌ No](https://app.tformance.com/survey/abc123/author?vote=no)

**Reviewers** - How was this code?
→ [😕 Could be better](https://app.tformance.com/survey/abc123/review?vote=1) · [👍 OK](https://app.tformance.com/survey/abc123/review?vote=2) · [🚀 Super](https://app.tformance.com/survey/abc123/review?vote=3)
<!-- tformance-survey-end -->
```

### One-Click Voting Flow

```
PR Description Link                OAuth (if needed)              Thank You Page
┌────────────────┐               ┌────────────────┐             ┌────────────────┐
│ 🚀 Super       │ ─── click ──► │ Authorize      │ ─── ok ───► │ ✅ Recorded!   │
│ (shared link)  │               │ tformance      │             │                │
└────────────────┘               └────────────────┘             │ Secondary Q:   │
                                                                │ Was AI used?   │
                                                                │ [Yes] [No]     │
                                                                │                │
                                                                │ [Change vote]  │
                                                                └────────────────┘
```

### AI Co-Author Detection

Patterns to detect in commit messages:
```python
AI_COAUTHOR_PATTERNS = [
    r"Co-Authored-By:.*GitHub Copilot",
    r"Co-Authored-By:.*Copilot",
    r"Co-Authored-By:.*Claude",
    r"Co-Authored-By:.*ChatGPT",
    r"Co-Authored-By:.*Cursor",
    r"Co-Authored-By:.*Codeium",
    r"Co-Authored-By:.*Tabnine",
    r"🤖 Generated with",  # Claude Code signature
    r"Generated by AI",
]
```

When detected:
1. Auto-set `author_ai_assisted = True`
2. Set `author_response_source = "auto"`
3. Skip the author question in PR description
4. Still ask reviewers for quality feedback

---

## Implementation Phases

### Phase 0: AI Auto-Detection (NEW)
**Effort**: S (2-3 hours)
**Risk**: Low
**Priority**: HIGH - Reduces survey fatigue

1. Create AI co-author detection service
2. Scan commit messages on PR merge
3. Auto-mark surveys when AI signature found
4. Update survey dispatch to skip author question

### Phase 1: PR Description Survey Delivery (Changed from Comment)
**Effort**: L (6-8 hours)
**Risk**: Medium (PR description modification)
**Priority**: HIGH - Enables one-click voting

1. Create GitHub PR description update service
2. Design description template with voting links
3. Use HTML comment markers for section identification
4. Implement Celery task for immediate update

### Phase 2: One-Click Voting System
**Effort**: L (8-10 hours)
**Risk**: Medium (OAuth flow complexity)
**Priority**: HIGH - Main UX improvement

1. Create one-click vote view with URL parameter handling
2. Implement GitHub OAuth for user identification
3. Build thank you page with secondary question
4. Handle vote changes and duplicates

### Phase 3: Slack Fallback Integration
**Effort**: M (4-6 hours)
**Risk**: Low (modifying existing system)

1. Implement 1-hour delayed Slack task
2. Check for existing responses before sending
3. Skip users who already responded via GitHub
4. Maintain backward compatibility

### Phase 4: Dashboard Metrics
**Effort**: L (6-8 hours)
**Risk**: Medium (new visualizations)

1. Response channel distribution chart
2. AI auto-detection rate
3. Modification effort breakdown
4. Response rate by channel comparison

---

## Technical Decisions

### Decision 1: PR Description Instead of Comment
**Choice**: Append survey to PR description, not post as comment
**Rationale**:
- Always visible at top of PR
- Doesn't add to comment noise
- Can be updated to show completion status
- User preference (like Coderabbit approach)

### Decision 2: AI Co-Author Auto-Detection
**Choice**: Scan commits for AI signatures, auto-mark when found
**Rationale**:
- Reduces survey fatigue
- More accurate data (no self-reporting needed)
- Respects developers' time
- Catches cases where author might forget to respond

### Decision 3: HTML Comment Markers
**Choice**: Use `<!-- tformance-survey-start/end -->` markers
**Rationale**:
- Can identify and update our section later
- Invisible to users viewing the PR
- Allows re-running without duplicating

### Decision 4: GitHub First, Slack Fallback
**Choice**: Update PR description immediately, delay Slack by 1 hour
**Rationale**:
- GitHub is where developers already are
- One-click reduces friction
- Slack fallback catches those who missed GitHub
- Deduplication prevents double-voting

### Decision 5: Response Source Tracking
**Choice**: Add `response_source` field with "auto" option
**Rationale**:
- Measure channel effectiveness
- Track auto-detection rate
- Optimize strategy over time

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PR description too long | Low | Medium | Compact design, separator line |
| GitHub OAuth complexity | Medium | High | Use existing allauth GitHub provider |
| Auto-detection false positives | Low | Medium | Conservative patterns, manual override |
| Missing AI signatures | Medium | Low | Fallback to manual survey still works |
| Migration issues | Low | Medium | All new fields nullable |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Survey response rate | Increase to >75% | Compare before/after one-click |
| AI auto-detection rate | >20% of PRs | Track response_source="auto" |
| GitHub vs Slack responses | 60%+ via GitHub | Track response_source field |
| Response time | <1 hour average | Time from PR merge to response |
| Dashboard load time | <2s | No performance regression |

---

## Dependencies

### New Dependencies
- GitHub App with `pull_requests: write` permission (for description update)
- PyGithub for PR update (already in use)

### Internal Dependencies
- `apps/metrics` - Core metrics app
- `apps/integrations` - GitHub integration
- `apps/web` - Survey views
- `apps/teams` - Team context
- `apps/users` - GitHub OAuth via allauth

---

## References

- Stack Overflow 2025 Developer Survey AI Section: https://survey.stackoverflow.co/2025/ai/
- Current PRSurvey model: `apps/metrics/models/surveys.py`
- GitHub webhook handler: `apps/integrations/views/webhooks.py`
- Slack survey service: `apps/integrations/services/slack_surveys.py`
