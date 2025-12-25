# OSS Projects Expansion - Plan

**Created:** 2025-12-24

## Objective

Add more open source projects to the seeding system to provide diverse data for AI detection testing and pattern validation.

## Current State

**7 projects** currently configured in `apps/metrics/seeding/real_projects.py`:

| Project | Repos | Max PRs | AI Adoption | Signal Type |
|---------|-------|---------|-------------|-------------|
| antiwork | 3 repos | 300/repo | 50% | High AI signal (Claude Code users) |
| polar | 4 repos | 300/repo | 45% | Medium signal |
| posthog | 4 repos | 200/repo | 40% | Large team, varied |
| fastapi | 1 repo | 300 | 30% | OSS framework |
| anthropic | 3 repos | 100 | 80% | AI company (expected high) |
| calcom | 1 repo | 150 | 35% | SaaS product |
| trigger | 1 repo | 100 | 40% | Dev tooling |

## Selection Criteria for New Projects

1. **Diverse AI tool coverage** - Projects using different tools (Cursor, Copilot, Claude, etc.)
2. **High activity** - 50+ PRs in last 90 days for meaningful sample
3. **PR description quality** - Teams that write detailed PR descriptions
4. **Multi-repo orgs** - Organizations with multiple active repos
5. **Known AI adopters** - Teams publicly discussing AI tool usage

## Proposed New Projects

### Tier 1: High AI Signal (Add First)

1. **Vercel** - `vercel/ai`, `vercel/next.js`, `vercel/vercel`
   - AI SDK maintainers, high Cursor/Copilot usage in community
   - Very active: 1000+ PRs/month across repos

2. **Supabase** - `supabase/supabase`, `supabase/realtime`, `supabase/edge-runtime`
   - Known AI-forward team, detailed PR descriptions
   - Growing team, varied technologies

3. **Langchain** - `langchain-ai/langchain`, `langchain-ai/langchainjs`
   - AI/LLM focused team, likely high AI tool usage
   - Python + TypeScript coverage

4. **Linear** - `linear/linear`
   - Highly polished product team, quality PRs
   - Known for developer tooling focus

### Tier 2: Varied Signal (Good for Diversity)

5. **Resend** - `resendlabs/resend`, `resendlabs/react-email`
   - Small focused team, modern stack
   - Known for quality engineering

6. **Deno** - `denoland/deno`, `denoland/fresh`
   - Rust + TypeScript, systems programming
   - Different AI usage patterns than web apps

7. **Railway** - `railwayapp/railway-cli`, `railwayapp/railway-docs`
   - Dev tooling company, likely Copilot users
   - CLI + docs repos (different content types)

8. **Neon** - `neondatabase/neon`, `neondatabase/serverless`
   - Postgres company, Rust + TypeScript
   - Enterprise engineering patterns

### Tier 3: Low/Unknown Signal (Control Group)

9. **SQLite** - `libsql/libsql`
   - Traditional systems programming
   - Likely lower AI tool adoption

10. **Hugo** - `gohugoio/hugo`
    - Mature Go project
    - Conservative development patterns

## Implementation Phases

### Phase 1: Infrastructure (if needed)
- Verify multi-repo seeding works correctly
- Test rate limiting with larger projects
- Add caching for large repos

### Phase 2: Add Tier 1 Projects
- Add Vercel (3 repos)
- Add Supabase (3 repos)
- Add Langchain (2 repos)
- Add Linear (1 repo)
- Seed and verify AI detection

### Phase 3: Add Tier 2 Projects
- Add remaining 4 projects
- Analyze detection rate differences

### Phase 4: Analysis & Refinement
- Compare detection rates across project types
- Identify missed patterns
- Update AI detection based on findings

## Config Template

```python
"vercel": RealProjectConfig(
    repos=(
        "vercel/ai",           # AI SDK
        "vercel/next.js",      # Main framework
        "vercel/vercel",       # CLI
    ),
    team_name="Vercel",
    team_slug="vercel-demo",
    max_prs=200,               # Per repo
    max_members=50,
    days_back=90,
    jira_project_key="VERC",
    ai_base_adoption_rate=0.45,  # High expected
    survey_response_rate=0.55,
    description="Vercel platform, Next.js, and AI SDK",
),
```

## Success Metrics

- **10+ diverse projects** seeded successfully
- **Detection rate variance** visible across project types
- **Pattern coverage** - identify gaps in current detection
- **LLM vs Regex comparison** data for more teams

## Dependencies

- GitHub token(s) with sufficient rate limits
- Working GraphQL fetcher
- Caching enabled (for large repos)
