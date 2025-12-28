# OSS Expansion - Tasks

**Last Updated**: 2025-12-26 18:05 UTC

---

## Completed

- [x] Research 75 new OSS product companies
- [x] Define 20 industry categories for benchmarking
- [x] Add `industry` field to `RealProjectConfig` dataclass
- [x] Add `INDUSTRIES` dictionary with display names
- [x] Add industry tags to existing 25 projects
- [x] Add Phase 1 projects (26-50) to `real_projects.py`
- [x] Add Phase 2 projects (51-100) to `real_projects.py`
- [x] Add helper functions: `get_projects_by_industry()`, `list_industries()`, `get_industry_display_name()`
- [x] Prepare parallel seeding commands with `--no-check-runs`

---

## In Progress

- [~] Seed Phase 1 projects (26-50) - **~23/25 done**
  - Terminal 1: growthbook 🔄, huly ⏳ (last 2 remaining)
  - Terminal 2: ✅ COMPLETE (all 13 done)

- [~] Seed Phase 2 projects (51-100) - **Started on T2**
  - Terminal 2: umami ✅, openreplay 🔄, 23 more pending

---

## Pending

### Phase 2 Seeding (T1 - starts after Phase 1)
- [ ] Run T1 Phase 2 command when huly finishes:
  - ollama → questdb (25 projects)

### LLM Analysis (SEPARATE STEP - not automatic!)
- [ ] Run `run_llm_batch` on all Phase 1 teams
- [ ] Run `run_llm_batch` on all Phase 2 teams

### Reporting
- [ ] Update AI-INSIGHTS-REPORT with industry breakdown
- [ ] Generate industry comparison data
- [ ] Consider dashboard views for industry benchmarks

---

## Future Enhancements

- [ ] Add industry benchmark views to analytics dashboard
- [ ] Create `/analytics/industry/` comparison page
- [ ] Add industry filter to PR list page
- [ ] Generate industry-specific AI adoption reports
