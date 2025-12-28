# OSS Expansion - Context

**Last Updated**: 2025-12-26 18:05 UTC
**Status**: Phase 1 Nearly Complete, Phase 2 Started

---

## Goal

Expand from 25 to 100 open source product companies for reliable AI impact research and industry benchmarking.

## Key Decisions Made

1. **Focus on Products, Not Frameworks** - SaaS alternatives, not language frameworks
2. **Industry Categories** - 20 categories defined for benchmarking comparisons
3. **Parallel Seeding** - Using 2 GitHub PATs in separate terminals to speed up
4. **2025 Data Only** - Using `--start-date 2025-01-01` for all seeding
5. **Skip Check Runs** - Using `--no-check-runs` to speed up seeding
6. **LLM Processing is Separate** - Seeding only imports to DB; `run_llm_batch` must be run after

---

## Current State (18:05 UTC)

### Database Stats

| Metric | Value |
|--------|-------|
| **Total PRs** | 99,445 |
| **Total Teams** | 54 (with PRs) |
| **Phase 1 Progress** | ~23/25 done |
| **Phase 2 Progress** | ~2/50 started |

### Active Seeding Processes (2 terminals running)

| Terminal | Current Project | Phase | Remaining in Queue |
|----------|-----------------|-------|--------------------|
| **T1** | growthbook 🔄 | Phase 1 | huly (last one) |
| **T2** | openreplay 🔄 | Phase 2 | 23 more projects |

### Phase 1 Team Status (26-50)

**Completed (23/25):**
- ✅ Chatwoot, Medusa, Appsmith, n8n, Strapi, AFFiNE
- ✅ Dify, PocketBase, Plausible, SigNoz
- ✅ Erxes, Mattermost, Saleor, ToolJet, Directus, Typebot
- ✅ Appwrite, Ghost, Zitadel, Flowise, Outline, Budibase, Webstudio

**In Progress:**
- 🔄 GrowthBook (T1 currently processing)

**Pending:**
- ⏳ Huly (T1 next - last Phase 1 project)

### Phase 2 Status (51-100)

**Terminal 2 (running):**
- ✅ Umami
- 🔄 OpenReplay (currently processing)
- ⏳ 23 more: matomo, hyperswitch, killbill, penpot, excalidraw, activepieces, automatisch, windmill, hasura, parse, laravel, remix, astro, nuxt, svelte, flagsmith, unleash, heyform, papercups, focalboard, taiga, rallly, erpnext

**Terminal 1 (starts after Phase 1):**
- ⏳ 25 projects: ollama, openwebui, lobechat, continue, jan, portainer, netdata, grafana, traefik, spree, bagisto, payload, keystone, rocketchat, zulip, appflowy, logseq, silverbullet, nocodb, baserow, illa, keycloak, casdoor, surrealdb, questdb

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `apps/metrics/seeding/real_projects.py` | Added `industry` field to dataclass, added `INDUSTRIES` dict (20 categories), added 75 new project configs (now 100 total), added helper functions |

---

## Commands Reference

### Check Seeding Progress
```bash
# Running processes
ps aux | grep seed_real_projects | grep -v grep

# Database stats
psql -d tformance -c "SELECT COUNT(DISTINCT team_id) as teams, COUNT(*) as prs FROM metrics_pullrequest"

# Or via Django
.venv/bin/python -c "import os; os.environ['DJANGO_SETTINGS_MODULE']='tformance.settings'; import django; django.setup(); from apps.metrics.models import PullRequest; print(f'PRs: {PullRequest.objects.count()}')"
```

### Terminal 1 - Phase 2 Command (run when huly finishes)
```bash
export GITHUB_SEEDING_TOKENS="PAT_1"
for project in ollama openwebui lobechat continue jan portainer netdata grafana traefik spree bagisto payload keystone rocketchat zulip appflowy logseq silverbullet nocodb baserow illa keycloak casdoor surrealdb questdb; do
  .venv/bin/python manage.py seed_real_projects --project "$project" --start-date 2025-01-01 --no-pr-limit --no-member-limit --no-check-runs --checkpoint-file ".checkpoint_p2_t1.json"
done
```

### After Seeding: LLM Analysis

**IMPORTANT: Seeding does NOT run LLM analysis automatically!**

Run for each new team after seeding completes:
```bash
export GROQ_API_KEY=$(grep "^GROQ_API_KEY=" .env | cut -d= -f2)

# List teams needing LLM analysis
psql -d tformance -c "SELECT t.name, COUNT(pr.id) as prs FROM teams_team t JOIN metrics_pullrequest pr ON pr.team_id = t.id WHERE pr.llm_summary IS NULL GROUP BY t.name ORDER BY COUNT(pr.id) DESC"

# Run batch for a team
.venv/bin/python manage.py run_llm_batch --team "TeamName" --limit 2000 --with-fallback
```

---

## Industry Distribution (100 projects)

| Industry | Count |
|----------|-------|
| DevOps/Infrastructure | 12 |
| AI & LLM Tools | 11 |
| Analytics & Observability | 10 |
| Internal Tools | 7 |
| CMS | 6 |
| Communication | 5 |
| Knowledge Management | 5 |
| E-commerce | 5 |
| BaaS | 5 |
| Identity/Security | 5 |
| Automation | 5 |
| Project Management | 5 |
| Billing | 4 |
| Feature Flags | 4 |
| Forms | 4 |
| Design | 4 |
| Database | 3 |
| CRM | 3 |
| Scheduling | 3 |
| Customer Support | 2 |

---

## New Helper Functions Added

```python
from apps.metrics.seeding.real_projects import (
    get_projects_by_industry,  # Get all projects in an industry
    list_industries,           # Get industry -> count dict
    get_industry_display_name, # Get display name for industry key
)
```

---

## Next Steps After Context Reset

1. **Check seeding status**: `ps aux | grep seed_real_projects`
2. **When T1 finishes Phase 1** (huly): Start Phase 2 T1 command above
3. **Monitor both terminals** until all 100 projects seeded (~2-3 hours total)
4. **Run LLM analysis** on all new teams (separate step!)
5. **Update AI-INSIGHTS-REPORT** with expanded 100-project dataset
6. Consider building industry comparison dashboard views
