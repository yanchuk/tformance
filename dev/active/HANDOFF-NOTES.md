# Session Handoff Notes

**Last Updated: 2025-12-26 18:05 UTC**

## Current Session: OSS Expansion Seeding

### Active Work

**2 Terminal processes running seeding:**

| Terminal | Current | Phase | Status |
|----------|---------|-------|--------|
| T1 | growthbook | Phase 1 | 🔄 2 left (growthbook, huly) |
| T2 | openreplay | Phase 2 | 🔄 24 left |

### Database Stats

| Metric | Value |
|--------|-------|
| **Total PRs** | 99,445 |
| **Total Teams** | 54 |
| **Phase 1** | ~23/25 done |
| **Phase 2** | ~2/50 done |

### Key Discovery This Session

**LLM processing is NOT automatic!**

The `seed_real_projects` command only:
1. Fetches PR data from GitHub GraphQL
2. Creates Team, TeamMember, PullRequest records
3. Simulates Jira/surveys

**LLM analysis must be run separately:**
```bash
export GROQ_API_KEY=$(grep "^GROQ_API_KEY=" .env | cut -d= -f2)
.venv/bin/python manage.py run_llm_batch --team "TeamName" --limit 2000 --with-fallback
```

---

## When T1 Finishes Phase 1 (huly)

Run this command in Terminal 1:

```bash
export GITHUB_SEEDING_TOKENS="PAT_1"
for project in ollama openwebui lobechat continue jan portainer netdata grafana traefik spree bagisto payload keystone rocketchat zulip appflowy logseq silverbullet nocodb baserow illa keycloak casdoor surrealdb questdb; do
  .venv/bin/python manage.py seed_real_projects --project "$project" --start-date 2025-01-01 --no-pr-limit --no-member-limit --no-check-runs --checkpoint-file ".checkpoint_p2_t1.json"
done
```

---

## After All Seeding Completes

### 1. Check which teams need LLM analysis
```bash
psql -d tformance -c "SELECT t.name, COUNT(pr.id) as prs FROM teams_team t JOIN metrics_pullrequest pr ON pr.team_id = t.id WHERE pr.llm_summary IS NULL GROUP BY t.name ORDER BY COUNT(pr.id) DESC"
```

### 2. Run LLM batch for each team
```bash
export GROQ_API_KEY=$(grep "^GROQ_API_KEY=" .env | cut -d= -f2)
.venv/bin/python manage.py run_llm_batch --team "TeamName" --limit 2000 --with-fallback
```

---

## Previous Session: Report Improvements (UNCOMMITTED)

`docs/index.html` has uncommitted changes from previous session:
- Disclosures, CTAs, legal notes, team filter
- See commit command in `dev/active/report-improvements/` if needed

---

## Files Modified (OSS Expansion)

| File | Changes |
|------|---------|
| `apps/metrics/seeding/real_projects.py` | 100 project configs, industry field, helper functions |
| `dev/active/oss-expansion/oss-expansion-context.md` | Updated with current progress |
| `dev/active/oss-expansion/oss-expansion-tasks.md` | Updated task status |

---

## No Migrations Needed

Only seeding config changes. No Django model changes this session.

---

## Summary of Sessions

| Session | Status |
|---------|--------|
| OSS Expansion (100 projects) | **IN PROGRESS** - seeding running |
| Report Improvements | COMPLETE (uncommitted) |
| Research Report Critical Review | COMPLETE |
| GitHub Pages Report | COMPLETE |
| Groq Batch Improvements | COMPLETE |
