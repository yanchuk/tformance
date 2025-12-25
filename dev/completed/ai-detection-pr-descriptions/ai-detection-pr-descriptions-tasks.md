# AI Detection via PR Description Analysis - Tasks

**Last Updated: 2025-12-25**

## Status: ✅ COMPLETE

All phases of AI detection via PR descriptions are complete. Moving to dev/completed/.

---

## ✅ Phase 1: Regex Pattern Detection (v1.7.0)

- [x] AI signature patterns for 15+ tools
- [x] CodeRabbit text patterns (22 patterns)
- [x] Mintlify agent patterns (3 patterns)
- [x] 459 PRs detected (20.2% detection rate)
- [x] 117 tests for ai_detector.py

---

## ✅ Phase 2: LLM Prompt System (v6.0.0 → v6.3.2)

### v6.0.0 - Health Assessment
- [x] System prompt with health assessment guidelines
- [x] Response schema: ai, tech, summary, health sections
- [x] get_user_prompt() with 14+ context parameters
- [x] GroqBatchProcessor for batch LLM processing

### v6.1.0 - Additional Metadata
- [x] Milestone, assignees, linked_issues, jira_key
- [x] Author name, reviewers, review_comments

### v6.2.0 - Unified Context Builder
- [x] build_llm_pr_context() single function
- [x] Prior AI detection included for LLM confirmation

### v6.3.0 - Unified Timeline
- [x] TimelineEvent dataclass
- [x] build_timeline() and format_timeline() functions
- [x] Chronological events: COMMIT, REVIEW, COMMENT, MERGED
- [x] A/B testing: +5.8% accuracy improvement

### v6.3.1 - AI Product Feature Detection
- [x] Clarified AI as product feature vs coding tool
- [x] Gemini/Claude integration examples

### v6.3.2 - is_assisted Clarification
- [x] ANY AI usage = is_assisted: true
- [x] Brainstorm and review usage now correctly detected
- [x] 28/29 golden tests passing (96.55%)

---

## ✅ Phase 3: Jinja2 Template System

- [x] Templates in apps/metrics/prompts/templates/
- [x] Sections: ai_detection, tech_detection, health_assessment, etc.
- [x] render_system_prompt() and render_user_prompt()
- [x] export_promptfoo_config() for automated testing
- [x] 34 tests for template rendering

---

## ✅ Phase 4: Golden Test Suite

- [x] 29 test cases in golden_tests.py
- [x] Categories: POSITIVE, NEGATIVE, EDGE_CASE, TECH, SUMMARY, HEALTH
- [x] Timeline data included in test cases
- [x] Promptfoo export with assertions

---

## ✅ Phase 5: Database Integration

- [x] PullRequest.llm_summary JSONField
- [x] PullRequest.llm_summary_version CharField
- [x] GIN indexes for JSONB queries (migration 0020)
- [x] run_llm_analysis management command

---

## Test Commands

```bash
# Unit tests
.venv/bin/pytest apps/metrics/prompts/tests/ -v  # 34 tests
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -v

# Promptfoo evaluation
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=... npx promptfoo eval -c promptfoo.yaml  # 28/29 pass

# LLM analysis on PRs
.venv/bin/python manage.py run_llm_analysis --limit 50
```

---

## Known Limitations

1. **neg_ai_as_product test**: Author name "Pat AI" causes false positive
2. **Aider/Windsurf**: Limited regex patterns (marked as xfail in golden tests)
3. **Rate limiting**: Groq free tier requires 2s delay between calls
