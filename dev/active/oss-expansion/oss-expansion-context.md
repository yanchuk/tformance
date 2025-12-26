# OSS Expansion - Context

**Last Updated**: 2025-12-26 17:00 UTC
**Status**: In Progress - Seeding Phase 1

---

## Goal

Expand from 25 to 100 open source product companies for reliable AI impact research and industry benchmarking.

## Key Decisions Made

1. **Focus on Products, Not Frameworks** - SaaS alternatives, not language frameworks
2. **Industry Categories** - 20 categories defined for benchmarking comparisons
3. **Parallel Seeding** - Using 2 GitHub PATs in separate terminals to speed up
4. **2025 Data Only** - Using `--start-date 2025-01-01` for all seeding
5. **Skip Check Runs** - Using `--no-check-runs` to speed up seeding

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `apps/metrics/seeding/real_projects.py` | Added `industry` field to dataclass, added `INDUSTRIES` dict (20 categories), added 75 new project configs (now 100 total), added helper functions |

---

## Current State

### Seeding Progress

| Phase | Projects | Range | Status |
|-------|----------|-------|--------|
| Original | 25 | antiwork → compai | ✅ Already seeded |
| Phase 1 | 25 | chatwoot → webstudio | 🔄 Seeding in progress |
| Phase 2 | 50 | ollama → erpnext | ⏳ Configs ready, pending |

### Industry Distribution (100 projects)

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

## Commands for Seeding

### Phase 1 (Currently Running)

**Terminal 1:**
```bash
export GITHUB_SEEDING_TOKENS="PAT_1"
for project in chatwoot medusa appsmith n8n strapi affine dify pocketbase plausible signoz growthbook huly; do
  .venv/bin/python manage.py seed_real_projects --project "$project" --start-date 2025-01-01 --no-pr-limit --no-member-limit --no-check-runs --checkpoint-file ".checkpoint_t1.json"
done
```

**Terminal 2:**
```bash
export GITHUB_SEEDING_TOKENS="PAT_2"
for project in erxes mattermost saleor tooljet directus typebot appwrite ghost zitadel flowise outline budibase webstudio; do
  .venv/bin/python manage.py seed_real_projects --project "$project" --start-date 2025-01-01 --no-pr-limit --no-member-limit --no-check-runs --checkpoint-file ".checkpoint_t2.json"
done
```

### Phase 2 (Run After Phase 1)

**Terminal 1:**
```bash
export GITHUB_SEEDING_TOKENS="PAT_1"
for project in ollama openwebui lobechat continue jan portainer netdata grafana traefik spree bagisto payload keystone rocketchat zulip appflowy logseq silverbullet nocodb baserow illa keycloak casdoor surrealdb questdb; do
  .venv/bin/python manage.py seed_real_projects --project "$project" --start-date 2025-01-01 --no-pr-limit --no-member-limit --no-check-runs --checkpoint-file ".checkpoint_p2_t1.json"
done
```

**Terminal 2:**
```bash
export GITHUB_SEEDING_TOKENS="PAT_2"
for project in umami openreplay matomo hyperswitch killbill penpot excalidraw activepieces automatisch windmill hasura parse laravel remix astro nuxt svelte flagsmith unleash heyform papercups focalboard taiga rallly erpnext; do
  .venv/bin/python manage.py seed_real_projects --project "$project" --start-date 2025-01-01 --no-pr-limit --no-member-limit --no-check-runs --checkpoint-file ".checkpoint_p2_t2.json"
done
```

---

## After Seeding: LLM Analysis

Run for each new team after seeding completes:
```bash
export GROQ_API_KEY=$(grep "^GROQ_API_KEY=" .env | cut -d= -f2)
.venv/bin/python manage.py run_llm_batch --team "TeamName" --limit 2000 --with-fallback
```

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

1. Check if Phase 1 seeding completed in terminals
2. Start Phase 2 seeding with commands above
3. Run LLM analysis on all new teams
4. Update AI-INSIGHTS-REPORT with industry breakdown
5. Consider building industry comparison dashboard views
