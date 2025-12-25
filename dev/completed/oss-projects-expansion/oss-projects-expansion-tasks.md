# OSS Projects Expansion - Tasks

**Last Updated:** 2025-12-24

## Phase 1: Add Tier 1 Projects (High AI Signal) ✅

- [x] Add Vercel configuration (vercel/ai, vercel/next.js, vercel/vercel)
- [x] Add Supabase configuration (supabase/supabase, supabase/realtime, supabase/supabase-js)
- [x] Add Langchain configuration (langchain-ai/langchain, langchain-ai/langchainjs)
- [x] Add Linear configuration (linearapp/linear)
- [ ] Test seeding for each new project
- [ ] Verify AI detection rates

## Phase 2: Add Tier 2 Projects (Varied Signal) ✅

- [x] Add Resend configuration (resend/resend-node, resend/react-email)
- [x] Add Deno configuration (denoland/deno, denoland/fresh)
- [x] Add Neon configuration (neondatabase/neon, neondatabase/serverless)
- [ ] Test seeding for each

## Phase 3: Test Seeding ✅

- [x] Seed Vercel project (90 PRs, 1.1% AI detected)
- [x] Seed Supabase project (90 PRs, 1.1% AI detected)
- [x] Seed Langchain project (60 PRs, 5.0% AI detected)

## Phase 4: Analysis (Pending)

- [ ] Run LLM detection on new projects
- [ ] Compare regex vs LLM detection rates
- [ ] Document pattern gaps
- [ ] Update AI detection patterns if needed

## Verification Commands

```bash
# Seed a single project
python manage.py seed_real_projects --project vercel

# Seed with cache refresh
python manage.py seed_real_projects --project vercel --refresh

# Check detection stats after seeding
python manage.py run_llm_experiment --team "Vercel" --limit 50
```

## Notes

- Start with smaller repos to validate pipeline
- Monitor GitHub rate limits during seeding
- Use `--no-cache` flag for fresh data if needed
