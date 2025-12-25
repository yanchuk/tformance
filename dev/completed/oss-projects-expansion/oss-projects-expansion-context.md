# OSS Projects Expansion - Context

**Last Updated:** 2025-12-24

## Session Summary (2025-12-24)

Added **7 new OSS projects** to `apps/metrics/seeding/real_projects.py`:

### Tier 1: High AI Signal
- **Vercel** (3 repos): vercel/ai, vercel/next.js, vercel/vercel
- **Supabase** (3 repos): supabase/supabase, supabase/realtime, supabase/supabase-js
- **LangChain** (2 repos): langchain-ai/langchain, langchain-ai/langchainjs
- **Linear** (1 repo): linearapp/linear

### Tier 2: Varied Signal
- **Resend** (2 repos): resend/resend-node, resend/react-email
- **Deno** (2 repos): denoland/deno, denoland/fresh
- **Neon** (2 repos): neondatabase/neon, neondatabase/serverless

**Total: 14 projects** (was 7)

### All 14 Projects Seeded - Detection Rates

| Team | PRs | Regex Detection |
|------|-----|-----------------|
| **Resend** | 200 | **83.0%** |
| **Cal.com** | 200 | **62.5%** |
| Antiwork | 44 | 31.8% |
| Anthropic | 124 | 27.4% |
| Gumroad | 224 | 24.1% |
| Neon | 17 | 5.9% |
| LangChain | 60 | 5.0% |
| Trigger.dev | 200 | 4.5% |
| PostHog | 657 | 2.7% |
| Linear | 94 | 2.1% |
| Polar.sh | 300 | 1.7% |
| Vercel | 90 | 1.1% |
| Supabase | 90 | 1.1% |
| Deno | 231 | 0.4% |

**Total: 434/2,531 PRs = 17.1% AI-assisted**

**Key Findings:**
1. **Resend (83%)** - Likely has team AI disclosure policy
2. **Cal.com (62.5%)** - Strong disclosure culture
3. **AI companies vary** - Anthropic 27%, LangChain 5%, Vercel 1%
4. **Systems projects low** - Deno 0.4% (Rust/systems programming)
5. LLM detection needed to catch implicit patterns in low-disclosure teams

## Purpose

Expand the real project seeding system to include more open source projects, providing diverse data for:
1. AI detection pattern testing
2. LLM vs regex detection comparison
3. Technology category detection validation
4. Dashboard data variety for demos

## Current Detection Stats (From AI Detection Context)

| Team | PRs | Regex Detection | LLM Est. |
|------|-----|-----------------|----------|
| Antiwork | 41 | 43.9% | ~70% |
| Cal.com | 199 | 32.7% | ~52% |
| Anthropic | 112 | 30.4% | ~49% |
| Gumroad | 221 | 29.9% | ~48% |
| PostHog | 637 | 2.7% | ~4% |
| Trigger.dev | 145 | 2.8% | ~4% |
| Polar.sh | 194 | 0.5% | ~1% |

**Key Finding:** LLM detection shows ~60% improvement over regex.

## Why More Projects?

1. **Pattern Validation** - Current detection patterns tuned on limited data
2. **Diverse Technologies** - Need Python, Rust, Go, TypeScript samples
3. **Team Size Variance** - Large corps vs small startups
4. **AI Tool Variance** - Different tools have different disclosure patterns

## Technical Context

### Seeding Pipeline

```
RealProjectConfig → GitHubGraphQLFetcher → RealProjectSeeder → Database
                          ↓
                    Local PR Cache (.seeding_cache/)
```

### Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/seeding/real_projects.py` | Project configurations |
| `apps/metrics/seeding/real_project_seeder.py` | Orchestrator |
| `apps/metrics/seeding/github_graphql_fetcher.py` | GraphQL API client |
| `apps/metrics/management/commands/seed_real_projects.py` | Management command |

### Rate Limiting

- GitHub GraphQL: 5,000 points/hour
- Large repos need token pooling or caching
- Cache persists in `.seeding_cache/{org}/{repo}.json`

## Related Active Work

- **ai-detection-pr-descriptions** - LLM detection improvements (Phase 2.7 next)
- **incremental-seeding** - Rate limit handling

## Success Criteria

1. 10+ projects seeded with real data
2. Detection rate comparison across project types
3. Pattern gaps identified and documented
4. Demo dashboard shows diverse team data
