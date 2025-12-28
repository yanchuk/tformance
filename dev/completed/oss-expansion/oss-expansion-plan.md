# OSS Project Expansion Plan: 25 → 50 → 100 Projects

**Goal**: Expand seeding from 25 to 100 open source product companies for industry benchmarking.

**Focus**: Products (SaaS alternatives), not frameworks/languages.

---

## Current State: 25 Projects

| # | Project | Category |
|---|---------|----------|
| 1 | Antiwork | Creator Economy |
| 2 | Polar.sh | Payments/Monetization |
| 3 | PostHog | Product Analytics |
| 4 | FastAPI | Framework (exclude?) |
| 5 | Anthropic | AI/LLM |
| 6 | Cal.com | Scheduling |
| 7 | Trigger.dev | Background Jobs |
| 8 | Vercel | DevOps/Deployment |
| 9 | Supabase | Database/BaaS |
| 10 | LangChain | AI/LLM |
| 11 | Linear | Project Management |
| 12 | Resend | Email Infrastructure |
| 13 | Deno | Runtime (exclude?) |
| 14 | Neon | Database |
| 15 | Twenty CRM | CRM |
| 16 | Novu | Notifications |
| 17 | Hoppscotch | API Testing |
| 18 | Plane | Project Management |
| 19 | Documenso | Document Signing |
| 20 | Coolify | Self-hosting/PaaS |
| 21 | Infisical | Secrets Management |
| 22 | Dub | Link Management |
| 23 | Lago | Billing |
| 24 | Formbricks | Surveys |
| 25 | Comp AI | Compliance |

---

## Industry Categories for Benchmarking

### 1. CRM & Sales Tools
Compare sales cycles, AI adoption in sales automation.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Twenty CRM | twentyhq/twenty | 25k+ | Modern Salesforce alt |
| **Erxes** | erxes/erxes | 3.5k | HubSpot/Zendesk combo |
| **Monica** | monicahq/monica | 21k | Personal CRM |

### 2. Project Management
Compare velocity, sprint patterns, team coordination.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Plane | makeplane/plane | 30k+ | Linear/Jira alt |
| Linear | linearapp/linear | - | Reference (partial OSS) |
| **Huly** | hcengineering/huly | 15k+ | All-in-one workspace |
| **Focalboard** | mattermost/focalboard | 21k | Notion/Trello alt |
| **OpenProject** | opf/openproject | 9k | Enterprise PM |
| **Vikunja** | go-vikunja/api | 1k | Task management |

### 3. Developer Infrastructure
Compare CI/CD, deployment patterns, DevOps metrics.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Vercel | vercel/vercel, vercel/next.js | 100k+ | Deployment |
| Coolify | coollabsio/coolify | 35k+ | Self-hosted Heroku |
| **Dokploy** | dokploy/dokploy | 10k+ | Self-hosted Vercel |
| **CapRover** | caprover/caprover | 13k | PaaS |
| **Render** | render-oss/* | - | (partial OSS) |

### 4. Product Analytics & Observability
Compare instrumentation, data collection patterns.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| PostHog | PostHog/posthog | 23k+ | Full analytics |
| **Plausible** | plausible/analytics | 20k+ | Privacy analytics |
| **Umami** | umami-software/umami | 23k+ | Simple analytics |
| **SigNoz** | SigNoz/signoz | 19k+ | DataDog alt |
| **Grafana** | grafana/grafana | 65k+ | Observability |
| **OpenStatus** | openstatusHQ/openstatus | 6k | Uptime monitoring |

### 5. Communication & Notifications
Compare messaging patterns, notification delivery.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Novu | novuhq/novu | 35k+ | Notification infra |
| Resend | resend/* | - | Email API |
| **Chatwoot** | chatwoot/chatwoot | 21k+ | Intercom alt |
| **Mattermost** | mattermost/mattermost | 31k | Slack alt |
| **Rocket.Chat** | RocketChat/Rocket.Chat | 41k | Team chat |
| **Zulip** | zulip/zulip | 22k | Team chat |

### 6. Customer Support & Helpdesk
Compare ticket resolution, support metrics.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Chatwoot | chatwoot/chatwoot | 21k+ | Intercom/Zendesk alt |
| **FreeScout** | freescout-helpdesk/freescout | 2.5k | HelpScout alt |
| **Zammad** | zammad/zammad | 4.5k | Helpdesk |
| **Peppermint** | Peppermint-Lab/peppermint | 2k | Issue management |

### 7. Security & Compliance
Compare security practices, audit patterns.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Infisical | Infisical/infisical | 16k+ | Secrets mgmt |
| Comp AI | trycompai/comp | 2k+ | SOC2/ISO compliance |
| **Zitadel** | zitadel/zitadel | 9k | Identity mgmt |
| **Keycloak** | keycloak/keycloak | 24k+ | IAM |
| **SuperTokens** | supertokens/supertokens-core | 13k | Auth |

### 8. Billing & Payments
Compare monetization, billing patterns.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Lago | getlago/lago | 7k+ | Usage billing |
| Polar.sh | polarsource/polar | 3k+ | Creator monetization |
| **Kill Bill** | killbill/killbill | 4.5k | Subscription billing |
| **Lotus** | uselotus/lotus | 1.5k | Metering |

### 9. Scheduling & Productivity
Compare calendar patterns, booking flows.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Cal.com | calcom/cal.com | 33k+ | Calendly alt |
| Documenso | documenso/documenso | 8k+ | DocuSign alt |
| **Typebot** | baptisteArno/typebot.io | 7k+ | Conversational forms |
| **Rallly** | lukevella/rallly | 3.5k | Poll scheduling |

### 10. Surveys & Forms
Compare response collection, form building.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Formbricks | formbricks/formbricks | 8k+ | Qualtrics alt |
| Typebot | baptisteArno/typebot.io | 7k+ | Chatbot forms |
| **OpnForm** | JhumanJ/OpnForm | 3k | Form builder |

### 11. Database & Backend-as-a-Service
Compare data patterns, API design.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Supabase | supabase/supabase | 75k+ | Firebase alt |
| Neon | neondatabase/neon | 15k+ | Serverless Postgres |
| **PocketBase** | pocketbase/pocketbase | 42k+ | Backend in 1 file |
| **Appwrite** | appwrite/appwrite | 46k+ | BaaS |
| **NHost** | nhost/nhost | 8k | GraphQL BaaS |

### 12. E-Commerce & Marketplaces
Compare transaction patterns, checkout flows.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| **Medusa** | medusajs/medusa | 26k+ | Shopify alt |
| **Saleor** | saleor/saleor | 21k+ | GraphQL commerce |
| **Vendure** | vendure-ecommerce/vendure | 6k | TypeScript commerce |
| **Bagisto** | bagisto/bagisto | 15k | Laravel commerce |

### 13. Headless CMS
Compare content patterns, publishing workflows.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| **Strapi** | strapi/strapi | 65k+ | Node.js CMS |
| **Directus** | directus/directus | 29k+ | Database CMS |
| **Payload** | payloadcms/payload | 29k+ | TypeScript CMS |
| **Ghost** | TryGhost/Ghost | 48k+ | Publishing |
| **TinaCMS** | tinacms/tinacms | 12k | Git-backed CMS |

### 14. AI/LLM Tools & Platforms
Compare AI adoption, model usage patterns.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| LangChain | langchain-ai/langchain | 100k+ | LLM framework |
| Anthropic | anthropics/* | - | AI company |
| **Dify** | langgenius/dify | 58k+ | LLM app platform |
| **Flowise** | FlowiseAI/Flowise | 33k+ | LLM chatbot builder |
| **Langflow** | langflow-ai/langflow | 36k+ | Visual LLM builder |
| **Open WebUI** | open-webui/open-webui | 55k+ | ChatGPT alt UI |
| **AnythingLLM** | Mintplex-Labs/anything-llm | 30k+ | All-in-one LLM |
| **Ollama** | ollama/ollama | 110k+ | Local LLM runner |

### 15. Internal Tools & Low-Code
Compare developer productivity, tool building.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| **Appsmith** | appsmithorg/appsmith | 35k+ | Retool alt |
| **ToolJet** | ToolJet/ToolJet | 32k+ | Low-code platform |
| **Budibase** | Budibase/budibase | 23k+ | Internal tools |
| **Windmill** | windmill-labs/windmill | 12k+ | Scripts to apps |
| **NocoBase** | nocobase/nocobase | 14k+ | No-code platform |

### 16. Workflow Automation
Compare automation patterns, integration usage.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Trigger.dev | triggerdotdev/trigger.dev | 10k+ | Background jobs |
| **n8n** | n8n-io/n8n | 50k+ | Zapier alt |
| **Activepieces** | activepieces/activepieces | 11k+ | Automation |
| **Huginn** | huginn/huginn | 44k+ | Agents system |

### 17. API Development & Testing
Compare API design, testing patterns.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| Hoppscotch | hoppscotch/hoppscotch | 66k+ | Postman alt |
| **Insomnia** | Kong/insomnia | 35k+ | API client |
| **Bruno** | usebruno/bruno | 28k+ | API client |

### 18. Knowledge Management
Compare documentation, knowledge sharing.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| **AFFiNE** | toeverything/AFFiNE | 43k+ | Notion alt |
| **AppFlowy** | AppFlowy-IO/AppFlowy | 58k+ | Notion alt |
| **Logseq** | logseq/logseq | 33k+ | Knowledge graph |
| **Outline** | outline/outline | 29k+ | Team wiki |

### 19. Feature Flags & Experimentation
Compare rollout patterns, A/B testing.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| **GrowthBook** | growthbook/growthbook | 6k+ | Feature flags/A/B |
| **Flagsmith** | Flagsmith/flagsmith | 5k+ | Feature flags |
| **Unleash** | Unleash/unleash | 12k+ | Feature toggles |

### 20. Website Builders
Compare design patterns, publishing.

| Project | Repo | Stars | Notes |
|---------|------|-------|-------|
| **Webstudio** | webstudio-is/webstudio | 5k+ | Webflow alt |
| **Plasmic** | plasmicapp/plasmic | 5k | Visual builder |

---

## Expansion Plan

### Phase 1: 25 → 50 Projects (Tier 1)

**Add 25 high-quality product companies:**

| # | Project | Repo | Category |
|---|---------|------|----------|
| 26 | Chatwoot | chatwoot/chatwoot | Customer Support |
| 27 | Medusa | medusajs/medusa | E-Commerce |
| 28 | Appsmith | appsmithorg/appsmith | Internal Tools |
| 29 | n8n | n8n-io/n8n | Workflow Automation |
| 30 | Strapi | strapi/strapi | Headless CMS |
| 31 | AFFiNE | toeverything/AFFiNE | Knowledge Mgmt |
| 32 | Dify | langgenius/dify | AI/LLM Platform |
| 33 | PocketBase | pocketbase/pocketbase | Database/BaaS |
| 34 | Plausible | plausible/analytics | Analytics |
| 35 | SigNoz | SigNoz/signoz | Observability |
| 36 | GrowthBook | growthbook/growthbook | Feature Flags |
| 37 | Huly | hcengineering/huly | Project Mgmt |
| 38 | Erxes | erxes/erxes | CRM |
| 39 | Mattermost | mattermost/mattermost | Communication |
| 40 | Saleor | saleor/saleor | E-Commerce |
| 41 | ToolJet | ToolJet/ToolJet | Internal Tools |
| 42 | Directus | directus/directus | Headless CMS |
| 43 | Typebot | baptisteArno/typebot.io | Forms/Chatbot |
| 44 | Appwrite | appwrite/appwrite | BaaS |
| 45 | Ghost | TryGhost/Ghost | Publishing |
| 46 | Zitadel | zitadel/zitadel | Identity |
| 47 | Flowise | FlowiseAI/Flowise | AI/LLM |
| 48 | Outline | outline/outline | Knowledge Mgmt |
| 49 | Budibase | Budibase/budibase | Internal Tools |
| 50 | Webstudio | webstudio-is/webstudio | Website Builder |

### Phase 2: 50 → 100 Projects (Tier 2)

**Add 50 more diverse products:**

| # | Project | Repo | Category |
|---|---------|------|----------|
| 51 | Open WebUI | open-webui/open-webui | AI/LLM |
| 52 | Ollama | ollama/ollama | AI/LLM |
| 53 | AppFlowy | AppFlowy-IO/AppFlowy | Knowledge Mgmt |
| 54 | Logseq | logseq/logseq | Knowledge Mgmt |
| 55 | Bruno | usebruno/bruno | API Testing |
| 56 | Insomnia | Kong/insomnia | API Testing |
| 57 | Rocket.Chat | RocketChat/Rocket.Chat | Communication |
| 58 | Zulip | zulip/zulip | Communication |
| 59 | Umami | umami-software/umami | Analytics |
| 60 | Grafana | grafana/grafana | Observability |
| 61 | OpenStatus | openstatusHQ/openstatus | Monitoring |
| 62 | Payload | payloadcms/payload | Headless CMS |
| 63 | TinaCMS | tinacms/tinacms | Headless CMS |
| 64 | Vendure | vendure-ecommerce/vendure | E-Commerce |
| 65 | Bagisto | bagisto/bagisto | E-Commerce |
| 66 | Windmill | windmill-labs/windmill | Internal Tools |
| 67 | NocoBase | nocobase/nocobase | Low-Code |
| 68 | Activepieces | activepieces/activepieces | Automation |
| 69 | Huginn | huginn/huginn | Automation |
| 70 | Keycloak | keycloak/keycloak | Identity |
| 71 | SuperTokens | supertokens/supertokens-core | Auth |
| 72 | FreeScout | freescout-helpdesk/freescout | Helpdesk |
| 73 | Zammad | zammad/zammad | Helpdesk |
| 74 | Kill Bill | killbill/killbill | Billing |
| 75 | Rallly | lukevella/rallly | Scheduling |
| 76 | OpnForm | JhumanJ/OpnForm | Forms |
| 77 | NHost | nhost/nhost | BaaS |
| 78 | Focalboard | mattermost/focalboard | Project Mgmt |
| 79 | OpenProject | opf/openproject | Project Mgmt |
| 80 | Dokploy | dokploy/dokploy | DevOps |
| 81 | CapRover | caprover/caprover | DevOps |
| 82 | Flagsmith | Flagsmith/flagsmith | Feature Flags |
| 83 | Unleash | Unleash/unleash | Feature Flags |
| 84 | Langflow | langflow-ai/langflow | AI/LLM |
| 85 | AnythingLLM | Mintplex-Labs/anything-llm | AI/LLM |
| 86 | Monica | monicahq/monica | CRM |
| 87 | Plasmic | plasmicapp/plasmic | Website Builder |
| 88 | Firecrawl | mendableai/firecrawl | Web Scraping |
| 89 | Botpress | botpress/botpress | Chatbot |
| 90 | Cal.com Platform | calcom/platform | Scheduling SDK |
| 91 | Penpot | penpot/penpot | Design Tool |
| 92 | Excalidraw | excalidraw/excalidraw | Whiteboard |
| 93 | Tldraw | tldraw/tldraw | Whiteboard |
| 94 | Uptime Kuma | louislam/uptime-kuma | Monitoring |
| 95 | Paperless-ngx | paperless-ngx/paperless-ngx | Document Mgmt |
| 96 | Rallly | lukevella/rallly | Scheduling |
| 97 | Peppermint | Peppermint-Lab/peppermint | Helpdesk |
| 98 | Memos | usememos/memos | Notes |
| 99 | Immich | immich-app/immich | Photo Mgmt |
| 100 | Hoarder | hoarder-app/hoarder | Bookmarks |

---

## Industry Comparison Framework

### Metrics to Compare Across Industries

1. **AI Adoption Rate** - % of PRs using AI tools
2. **AI Tool Mix** - Which tools (Copilot, Cursor, Claude, etc.)
3. **Cycle Time** - Average time from PR open to merge
4. **Review Time** - Time to first review
5. **PR Size Distribution** - XS/S/M/L/XL breakdown
6. **Review Coverage** - % PRs with reviews
7. **CI Pass Rate** - Build success rate
8. **Contributor Count** - Active contributors
9. **Commit Frequency** - Commits per week
10. **Code Complexity** - Files changed per PR

### Industry Benchmarks to Generate

| Industry | Key Metrics | Sample Size Target |
|----------|-------------|-------------------|
| CRM & Sales | Cycle time, AI adoption | 5-8 teams |
| Project Management | Sprint velocity, PR size | 5-8 teams |
| Developer Infrastructure | CI/CD metrics, deployments | 8-10 teams |
| Analytics & Observability | Data complexity, review time | 5-8 teams |
| Communication | Real-time updates, test coverage | 5-8 teams |
| E-Commerce | Transaction safety, review rigor | 4-6 teams |
| AI/LLM Tools | AI adoption (meta!), innovation rate | 8-10 teams |
| Internal Tools | Low-code patterns, contributor diversity | 5-8 teams |

---

## Implementation Steps

### Step 1: Add Project Configs

Update `apps/metrics/seeding/real_projects.py`:

```python
# Add industry field to RealProjectConfig
@dataclass(frozen=True)
class RealProjectConfig:
    # ... existing fields ...
    industry: str = ""  # NEW: For benchmarking
```

### Step 2: Add New Projects

Add each project with its industry category:

```python
"chatwoot": RealProjectConfig(
    repos=("chatwoot/chatwoot",),
    team_name="Chatwoot",
    team_slug="chatwoot-demo",
    max_prs=300,
    max_members=50,
    days_back=90,
    jira_project_key="CHAT",
    ai_base_adoption_rate=0.40,
    industry="customer_support",
    description="Open source Intercom/Zendesk alternative",
),
```

### Step 3: Seed in Batches

```bash
# Phase 1: First 25 new projects
python manage.py seed_real_projects --project chatwoot
python manage.py seed_real_projects --project medusa
# ... etc

# Phase 2: Next 50 projects
python manage.py seed_real_projects --project openwebui
# ... etc
```

### Step 4: Run LLM Analysis

```bash
# Analyze all new teams
for team in "Chatwoot" "Medusa" "Appsmith" ...
do
    python manage.py run_llm_batch --team "$team" --limit 2000 --with-fallback
done
```

### Step 5: Generate Industry Reports

Create new analytics views for industry comparisons:

- `/analytics/industry/` - Cross-industry benchmark dashboard
- `/analytics/industry/{category}/` - Category-specific benchmarks

---

## Timeline Estimate

| Phase | Projects | Effort |
|-------|----------|--------|
| Phase 1 | 25 → 50 | Add configs, seed, analyze |
| Phase 2 | 50 → 100 | Add configs, seed, analyze |
| Reports | Industry dashboards | Build comparison views |

---

## Success Criteria

1. **100 product teams** seeded with real GitHub data
2. **20 industry categories** defined with 3-10 teams each
3. **Industry benchmarks** generated for key metrics
4. **AI Impact Report** expanded to industry comparisons
5. **Dashboard views** for cross-team industry analysis

---

## Sources

- [RunaCapital/awesome-oss-alternatives](https://github.com/RunaCapital/awesome-oss-alternatives)
- [YC Open Source Companies](https://www.ycombinator.com/companies/industry/open-source)
- [yc-oss/open-source-companies](https://github.com/yc-oss/open-source-companies)
- [OpenAlternative.co](https://openalternative.co/)
