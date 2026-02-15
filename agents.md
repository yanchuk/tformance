# Tformance Agents

Mission control for every automation or copiloted workflow in this repo. Agents operate on the same guardrails that humans do (`CLAUDE.md`) and should load supporting skills from `.agents/` (copied from the Claude skill library).

## Mission & Context
- Build the AI Impact Analytics platform for CTOs (GitHub/Jira/Slack signals + dashboards)
- Django 5.2.9 + Python 3.12 backend (Pegasus SaaS foundation)
- HTMX + Alpine.js + Tailwind (DaisyUI) front-end with Vite bundling
- Celery + Redis workers, PostgreSQL database, Groq for LLM work, Cloudflare tunnel + Docker staging environments

## Runbook
1. **Start locally**: `make dev` (Django + Vite dev servers). Use `.venv/bin/python` for any Django/pytest command.
2. **Validate**: `make test` for the default suite, `make ruff` for lint/format, `make e2e` for Playwright flows, `make celery` (solo pool) on macOS.
3. **Respect prompts**: Any changes under `apps/metrics/prompts/templates/*` require approval + `PROMPT_VERSION` bump in `apps/metrics/prompts/constants.py`.
4. **Keep data isolated**: Every `BaseTeamModel` query must go through `for_team` (or carry `# noqa: TEAM001 - reason`).
5. **Async discipline**: Never call `asyncio.run()` inside Django/Celery contexts. Use `async_to_sync` helpers.
6. **LLM data priority**: Prefer `effective_*` fields on PullRequest models (see `prd/AI-DETECTION-TESTING.md`).
7. **Docs first**: Product/architecture specs live in `prd/`. Execution plans, SEO guides, QA strategies, etc., live under `docs/` (e.g., `docs/plans/public-page-seo-audit.md`).

## Guardrails to Enforce
- `.venv/bin/` prefix for Python/Celery/Test commands
- Function-based views over class-based (unless DRF)
- No inline `<script>` tags in HTMX partials—use Alpine modules
- Team URLs vs. global URLs must follow existing patterns
- Split files approaching 300 lines into modules
- DaisyUI + Tailwind tokens for styling, Chart.js for dashboards

## Agent & Skill Catalog (`.agents/`)
| Agent Skill | What it Unlocks |
|-------------|-----------------|
| `chart-patterns` | Chart.js + Easy Eyes implementation patterns for dashboard visuals. |
| `cto-marketing-copy` | Messaging frameworks for CTO/developer buyers (landing/compare/pricing copy). |
| `django-dev-guidelines` | Canonical Django + Pegasus patterns (BaseModel, for_team, DRF, Celery). |
| `engineering-metrics-domain` | Domain expertise on DORA/PR velocity metrics and what CTOs care about. |
| `factory-pattern-guide` | Factory Boy usage for tests (Sequences, batch creation, placement). |
| `htmx-alpine-flowbite-guidelines` | Front-end patterns: HTMX interactions, Alpine state, DaisyUI/Flowbite components. |
| `integration-pipeline-flow` | Data pipeline knowledge from GitHub/Jira/Slack syncs into dashboards. |
| `plan-review` | Critiques generated plans; tighten gap analysis before execution. |
| `prompt-engineer` | Prompt-design best practices for Groq/GPT/Claude plus versioning expectations. |
| `seo-geo` | SEO + Generative Engine Optimization tactics (schema, meta, AI search visibility). |
| `service-layer-patterns` | How existing service classes orchestrate business logic (DashboardService, etc.). |
| `skill-developer` | Meta-guidance for editing/adding skills and `skill-rules.json` triggers. |
| `tdd-integration` | Enforces strict Red-Green-Refactor loops for new features. |
| `team-isolation-enforcer` | Watches for TEAM001 violations in ORM queries. |
| `writing-well` | Copy guidance from *On Writing Well* for UI/microcopy. |
| `skill-rules.json` | Trigger definitions controlling when skills should auto-fire. |

Each subdirectory keeps the original `SKILL.md` with YAML frontmatter. Agents should import whichever skill best matches their goal before executing changes.

## Documentation Map
- `CLAUDE.md` – canonical engineering guide (use as baseline for every agent)
- `prd/PRD-MVP.md`, `prd/ARCHITECTURE.md`, `prd/DATA-MODEL.md` – product + system design references
- `prd/AI-DETECTION-TESTING.md` – LLM signal processing + testing strategy
- `dev/guides/*.md` – commands, testing, frontend patterns, integrations, Copilot workflows
- `docs/plans/*.md` – current initiatives (SEO audits, growth plans, QA summaries, Jira/public app enhancements)

## Agent Workflow Checklist
1. Confirm task intent + relevant doc(s)
2. Load matching skill(s) from `.agents/`
3. Review guardrails (above) and any task-specific rules in `docs/`
4. Execute with TDD where features change behavior
5. Run appropriate tests/linters before handing off
6. Summarize findings + link back to files touched (line references) when reporting

Following this guide keeps human + automated contributors aligned on the same playbook.
