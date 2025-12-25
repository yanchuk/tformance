# Multi-Repo Seeding Expansion Plan

**Last Updated:** 2025-12-24

## Executive Summary

Expand the real project seeding infrastructure to fetch data from multiple repositories per organization. Currently, we sync only one repo per team (polarsource/polar and antiwork/gumroad). This plan adds support for additional active repositories from both organizations to provide richer demo data.

## Current State Analysis

### Existing Infrastructure
- `RealProjectConfig` dataclass supports single `repo_full_name` field
- `REAL_PROJECTS` registry maps project names to configs
- `RealProjectSeeder` orchestrates seeding for one repo per team
- `GitHubAuthenticatedFetcher` handles GitHub API calls with token pool
- Management command `seed_real_projects` provides CLI interface

### Current Seeded Repos
| Team | Repo | Stars | Status |
|------|------|-------|--------|
| Polar.sh | polarsource/polar | 8,901 | Synced |
| Antiwork | antiwork/gumroad | 7,808 | Synced |

### Active Repos Discovered (last 30 days)

**Polar (polarsource) - 10 active repos:**
| Repo | Stars | Open Issues | Notes |
|------|-------|-------------|-------|
| polar | 8,901 | 309 | Main product (already synced) |
| polar-js | 165 | 2 | JavaScript SDK |
| polar-php | 38 | 1 | PHP SDK |
| polar-python | 51 | 2 | Python SDK |
| examples | 6 | 1 | Example integrations |
| polar-adapters | 131 | 11 | Framework adapters |
| handbook | 3 | 1 | Company handbook |
| polar-init | 13 | 5 | CLI tool |
| polar-next-app | 31 | 4 | Next.js template |
| polar-go | 71 | 1 | Go SDK |

**Antiwork - 8 active repos:**
| Repo | Stars | Open Issues | Notes |
|------|-------|-------------|-------|
| gumroad | 7,808 | 126 | Main product (already synced) |
| flexile | 765 | 4 | HR/payroll platform |
| helper | 647 | 10 | Customer support tool |
| gum.new | 9 | 1 | Landing page creator |
| gumboard | 163 | 4 | Dashboard tool |
| iffy | 432 | 6 | Content moderation |
| .github | 1 | 0 | Org config |
| smallbets | 170 | 21 | Investment platform |

## Proposed Future State

### Target Configuration

**Polar Team - Add 3 repos (4 total):**
1. `polarsource/polar` (main product) - already synced
2. `polarsource/polar-adapters` (131 stars, framework integrations)
3. `polarsource/polar-python` (51 stars, Python SDK)
4. `polarsource/polar-js` (165 stars, JavaScript SDK)

**Antiwork Team - Add 2 repos (3 total):**
1. `antiwork/gumroad` (main product) - already synced
2. `antiwork/flexile` (765 stars, HR platform)
3. `antiwork/helper` (647 stars, support tool)

### Config Structure Change

```python
# Current
@dataclass
class RealProjectConfig:
    repo_full_name: str  # Single repo
    team_name: str
    team_slug: str
    ...

# Proposed
@dataclass
class RealProjectConfig:
    repos: list[str]  # Multiple repos
    team_name: str
    team_slug: str
    ...
```

## Implementation Phases

### Phase 1: Config Schema Update (Effort: S)
Modify `RealProjectConfig` to support multiple repositories while maintaining backward compatibility.

### Phase 2: Seeder Multi-Repo Support (Effort: M)
Update `RealProjectSeeder` to iterate over multiple repos and aggregate data under one team.

### Phase 3: Add New Repos to Registry (Effort: S)
Update `REAL_PROJECTS` with expanded repo lists for Polar and Gumroad.

### Phase 4: Execute Seeding (Effort: S)
Run seeding to fetch data from all new repos.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Rate limiting with more repos | Medium | Medium | Use token pool, add delays |
| Duplicate contributors across repos | High | Low | Dedupe by GitHub username |
| Large data volume | Low | Medium | Limit PRs per repo (50) |
| API timeout on large repos | Low | Medium | Existing retry logic |

## Success Metrics

- [ ] All 7 repos synced (4 Polar + 3 Antiwork)
- [ ] No duplicate team members
- [ ] PR technology categories show variety across repos
- [ ] Dashboard displays multi-repo data correctly

## Required Resources

- GitHub API tokens (already configured in `.env`)
- Minimal code changes (~50-100 lines)
- Seeding time: ~10-15 minutes with rate limiting
