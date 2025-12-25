# AI Detection Repositories Runbook

**Purpose**: How to add, configure, and manage target repositories for AI detection experiments.

---

## Repository Tiers

We organize repositories by expected AI disclosure signal strength:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        REPOSITORY TIERS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TIER 1: High Signal (AI disclosure culture)                            │
│  ├── antiwork/gumroad         68% have AI Disclosure section           │
│  ├── anthropic/anthropic-cookbook                                       │
│  ├── supabase/supabase                                                  │
│  └── cal-com/cal.com                                                    │
│                                                                          │
│  TIER 2: Medium Signal (AI tool repos - CAUTION)                        │
│  ├── vercel/ai                ⚠️ High false positive risk              │
│  ├── langchain-ai/langchain   ⚠️ Product mentions ≠ AI authoring       │
│  └── openai/openai-python                                               │
│                                                                          │
│  TIER 3: Low Signal (Traditional OSS)                                   │
│  ├── microsoft/vscode                                                   │
│  ├── facebook/react                                                     │
│  ├── django/django                                                      │
│  └── rails/rails                                                        │
│                                                                          │
│  TIER 4: Search-Based Discovery                                         │
│  └── gh search prs "Generated with Claude Code"                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Current Repository List

Location: `experiments/repos.yaml`

```yaml
# experiments/repos.yaml
tiers:
  tier1_high_signal:
    description: "Teams with AI disclosure culture"
    repos:
      - owner: antiwork
        repo: gumroad
        notes: "PRIMARY - 68% have AI Disclosure section"

      - owner: anthropic
        repo: anthropic-cookbook
        notes: "Claude creator - likely Claude Code usage"

      - owner: anthropic
        repo: courses
        notes: "Educational content"

      - owner: supabase
        repo: supabase
        notes: "AI-forward culture"

      - owner: cal-com
        repo: cal.com
        notes: "Indie dev team"

  tier2_ai_tools:
    description: "AI tool/framework repos - HIGH FALSE POSITIVE RISK"
    strategy: "Only look for Co-Authored-By and explicit signatures"
    repos:
      - owner: vercel
        repo: ai
        notes: "⚠️ Gemini/Claude mentions are product refs"

      - owner: langchain-ai
        repo: langchain
        notes: "⚠️ LLM product integrations"

      - owner: openai
        repo: openai-python
        notes: "⚠️ API product repo"

  tier3_traditional:
    description: "Traditional OSS - good for negative examples"
    repos:
      - owner: microsoft
        repo: vscode
        notes: "~60K PRs, established process"

      - owner: facebook
        repo: react
        notes: "Formal PR process"

      - owner: django
        repo: django
        notes: "Python, traditional"

      - owner: rails
        repo: rails
        notes: "Ruby, traditional"

  tier4_discovered:
    description: "Found via GitHub search"
    search_queries:
      - '"Generated with Claude Code"'
      - '"Co-Authored-By: Claude"'
      - '"AI Disclosure"'
    repos: []  # Populated dynamically
```

---

## Adding a New Repository

### Step 1: Evaluate the Repository

Before adding, check:

```bash
# 1. Check if repo has AI disclosure culture
gh api repos/owner/repo/pulls?state=all\&per_page=10 | jq '.[].body' | grep -i "ai disclosure"

# 2. Check for Claude Code signatures
gh search prs --repo owner/repo "Generated with Claude Code" --limit 10

# 3. Check for Co-Authored-By patterns
gh search prs --repo owner/repo "Co-Authored-By: Claude" --limit 10
```

### Step 2: Determine Tier

| Criteria | Tier |
|----------|------|
| Has "AI Disclosure" section in PRs | Tier 1 |
| AI tool/framework repo | Tier 2 (caution) |
| Traditional open source | Tier 3 |
| Found via search | Tier 4 |

### Step 3: Add to Config

```yaml
# experiments/repos.yaml
tiers:
  tier1_high_signal:
    repos:
      # Add new repo
      - owner: new-org
        repo: new-repo
        notes: "Why this repo is Tier 1"
```

### Step 4: Fetch Initial Data

```bash
# Fetch PRs from new repo
python apps/metrics/scripts/fetch_oss_prs.py \
  --repo new-org/new-repo \
  --limit 100

# Run detection experiment
python manage.py run_ai_detection_experiment \
  --repo new-org/new-repo \
  --experiment-name "new-repo-test" \
  --limit 50
```

---

## Fetching PRs from Repositories

### Using fetch_oss_prs.py

```bash
# Fetch from single repo
python apps/metrics/scripts/fetch_oss_prs.py --repo antiwork/gumroad --limit 100

# Fetch from all Tier 1 repos
python apps/metrics/scripts/fetch_oss_prs.py --tier 1

# Search across GitHub
python apps/metrics/scripts/fetch_oss_prs.py --search "Generated with Claude Code" --limit 100
```

### Output Format

```json
{
  "repo": "antiwork/gumroad",
  "number": 1635,
  "title": "Fix checkout flow",
  "body": "## AI Disclosure\nCursor (Claude 4.5 Sonnet) used...",
  "author": "developer",
  "created_at": "2025-01-15T10:00:00Z",
  "merged_at": "2025-01-16T14:00:00Z"
}
```

---

## Repository-Specific Strategies

### Tier 1: High Signal Repos

**Strategy**: Standard detection

```yaml
detection:
  strategy: "standard"
  include_signals:
    - tool_names
    - ai_disclosure_section
    - co_authored_by
    - phrases
```

### Tier 2: AI Tool Repos

**Strategy**: Explicit signatures only (avoid product mention false positives)

```yaml
detection:
  strategy: "explicit_only"
  include_signals:
    - co_authored_by
    - generated_with_signature
  exclude_signals:
    - tool_names  # Too many false positives
    - phrases
```

### Tier 3: Traditional Repos

**Strategy**: High precision (these likely have low AI usage)

```yaml
detection:
  strategy: "high_precision"
  confidence_threshold: 0.9
  require_explicit_signature: true
```

---

## Discovered Repositories

### GitHub Search Commands

```bash
# Find repos with Claude Code PRs
gh search prs "Generated with Claude Code" \
  --limit 100 \
  --json repository,number \
  | jq -r '.[].repository.nameWithOwner' | sort | uniq -c | sort -rn

# Find repos with AI Disclosure sections
gh search prs "AI Disclosure" \
  --limit 100 \
  --json repository \
  | jq -r '.[].repository.nameWithOwner' | sort | uniq -c | sort -rn

# Find repos with Co-Authored-By Claude
gh search prs "Co-Authored-By: Claude" \
  --limit 100 \
  --json repository \
  | jq -r '.[].repository.nameWithOwner' | sort | uniq -c | sort -rn
```

### Adding Discovered Repos

When you discover a new repo with AI disclosure culture:

```bash
# 1. Add to tier4_discovered
# 2. Evaluate signal strength
# 3. Optionally promote to Tier 1 if high quality
```

---

## Organizations to Monitor

These organizations are known to encourage AI tool usage:

```yaml
# experiments/organizations.yaml
organizations:
  - name: anthropic
    notes: "Claude creator"
    repos_to_watch:
      - anthropic-cookbook
      - courses
      - sdk

  - name: vercel
    notes: "AI SDK, Next.js"
    repos_to_watch:
      - ai
      - next.js

  - name: supabase
    notes: "Developer-focused"
    repos_to_watch:
      - supabase

  - name: cal-com
    notes: "Open source calendar"
    repos_to_watch:
      - cal.com
```

---

## Data Quality Considerations

### False Positive Sources (Tier 2)

| Repo | False Positive Risk | Reason |
|------|---------------------|--------|
| vercel/ai | HIGH | "Gemini", "Claude" are products they integrate |
| langchain-ai/langchain | HIGH | LLM product mentions everywhere |
| openai/openai-python | MEDIUM | API product repo |

### Mitigation

For Tier 2 repos:
1. Only count explicit signatures (`Co-Authored-By`, `Generated with`)
2. Ignore tool name mentions in code/docs
3. Manual review sample before trusting results

---

## Repository Statistics

Track these metrics per repo:

```python
# After running experiment
stats = {
    "repo": "antiwork/gumroad",
    "total_prs": 1700,
    "prs_with_body": 1650,
    "prs_with_ai_disclosure_section": 1100,
    "detection_rate_regex": 0.244,
    "detection_rate_llm": 0.71,
    "explicit_signatures": 450,
    "negative_disclosures": 650,
}
```

Save to: `experiments/results/repo_stats.json`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-24 | Initial runbook |
