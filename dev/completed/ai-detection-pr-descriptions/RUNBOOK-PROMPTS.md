# AI Detection Prompts Runbook

**Purpose**: How to create, modify, and version detection prompts for AI detection experiments.

---

## Prompt Structure

Each prompt has two parts:

1. **System Prompt** - Instructions for the LLM (cached, reused)
2. **User Template** - Per-PR content with placeholders

```
┌─────────────────────────────────────┐
│         SYSTEM PROMPT               │
│  - Detection rules                  │
│  - Positive/negative signals        │  ← Cached by provider
│  - Response format                  │
└─────────────────────────────────────┘
           +
┌─────────────────────────────────────┐
│         USER TEMPLATE               │
│  "Analyze this PR:\n\n{pr_body}"    │  ← Per-PR content
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│         JSON RESPONSE               │
│  is_ai_assisted, tools, confidence  │
└─────────────────────────────────────┘
```

---

## Current Prompt (v1)

Location: `experiments/prompts/v1.md`

```markdown
# System Prompt

You are an AI detection system analyzing pull requests to identify if AI coding assistants were used.

## Detection Rules

POSITIVE signals (AI was used):
1. Tool names: Cursor, Claude, Copilot, Cody, Aider, Devin, Gemini, Windsurf, Tabnine
2. In "AI Disclosure" section: Any usage statement like "Used for", "Used to", "Helped with"
3. Co-Authored-By with AI names or @anthropic.com/@cursor.sh emails
4. Phrases: "AI-generated", "AI-assisted", "generated with", "written by AI"

NEGATIVE signals (AI was NOT used):
1. Explicit denials: "No AI", "None", "Not used", "N/A"
2. AI as feature: "Add AI to dashboard" (building AI features ≠ using AI to code)
3. Past tense references: "Devin's previous PR" (referencing past work)

## Response Format

Return JSON with these fields:
- is_ai_assisted: boolean
- tools: list of lowercase tool names detected (e.g., ["cursor", "claude"])
- usage_category: "authored" | "assisted" | "reviewed" | "brainstorm" | null
- confidence: float 0.0-1.0
- reasoning: brief 1-sentence explanation
```

---

## Creating a New Prompt Version

### Step 1: Copy Current Prompt

```bash
cp experiments/prompts/v1.md experiments/prompts/v2.md
```

### Step 2: Edit the New Prompt

Common modifications:

**Add new tool detection:**
```diff
 POSITIVE signals (AI was used):
 1. Tool names: Cursor, Claude, Copilot, Cody, Aider, Devin, Gemini, Windsurf, Tabnine
+   Also detect: Supermaven, Continue, Codeium, Sourcery
```

**Improve ambiguous handling:**
```diff
 POSITIVE signals (AI was used):
+2. In "AI Disclosure" section: "Used for X" implies AI tool usage even without
+   explicit tool name. The section title indicates AI context.
```

**Add usage categories:**
```diff
 ## Response Format
 - usage_category:
+   - "authored": AI wrote most/all code
+   - "assisted": AI helped with specific parts
+   - "reviewed": AI reviewed the code
+   - "brainstorm": AI used for ideation only
```

### Step 3: Update Config

```yaml
# experiments/default.yaml
prompt:
  file: "prompts/v2.md"
```

### Step 4: Test New Prompt

```bash
# Test on 20 PRs
python manage.py run_ai_detection_experiment \
  --config experiments/test-v2.yaml \
  --experiment-name "prompt-v2-test" \
  --limit 20

# Compare with v1
python manage.py compare_experiments \
  --baseline "prompt-v1-baseline" \
  --current "prompt-v2-test"
```

### Step 5: Update Symlink

```bash
# If v2 is better
cd experiments/prompts
ln -sf v2.md current.md
```

---

## Prompt Versioning Guidelines

### Naming Convention

```
v<major>.<minor>.md
```

- **Major**: Significant logic changes (new signals, different categories)
- **Minor**: Refinements (better wording, edge cases)

Examples:
- `v1.0.md` - Initial prompt
- `v1.1.md` - Added Supermaven detection
- `v2.0.md` - Restructured with chain-of-thought
- `v2.1.md` - Fixed false positive on "AI feature"

### Change Log

Maintain a change log at the top of each prompt:

```markdown
# AI Detection Prompt v2.1

## Changelog
- v2.1: Fixed false positive when PR mentions "AI feature" as product work
- v2.0: Added chain-of-thought reasoning before JSON response
- v1.1: Added Supermaven, Continue, Codeium detection
- v1.0: Initial prompt with basic detection rules
```

---

## Testing Prompts

### Manual Testing

```python
from apps.integrations.services.groq_ai_detector import detect_ai_with_groq

# Test positive case
body = """
## AI Disclosure
Cursor (Claude 4.5 Sonnet) used for implementation
"""
result = detect_ai_with_groq(body)
print(result)  # Should be is_ai_assisted=True, tools=["cursor", "claude"]

# Test negative case
body = """
## AI Disclosure
No AI was used for this PR.
"""
result = detect_ai_with_groq(body)
print(result)  # Should be is_ai_assisted=False
```

### Batch Testing

```bash
# Create test cases file
cat > experiments/test_cases.jsonl << 'EOF'
{"id": 1, "body": "## AI Disclosure\nCursor used", "expected_ai": true, "expected_tools": ["cursor"]}
{"id": 2, "body": "## AI Disclosure\nNone", "expected_ai": false, "expected_tools": []}
{"id": 3, "body": "Added AI feature to dashboard", "expected_ai": false, "expected_tools": []}
EOF

# Run test suite
python manage.py test_detection_prompt \
  --cases experiments/test_cases.jsonl \
  --prompt experiments/prompts/v2.md
```

---

## Common Prompt Issues

### Issue 1: False Positives on AI Products

**Problem**: "Integrate Gemini API" flagged as AI-assisted

**Fix**: Add to NEGATIVE signals:
```markdown
2. AI as feature: Mentions of AI tools as products being integrated,
   not as authoring tools. Examples:
   - "Integrate Gemini API" - building AI features
   - "Add Claude support" - product integration
   - "Copilot SDK" - product reference
```

### Issue 2: Missing Implicit AI Usage

**Problem**: "Used for brainstorming" in AI Disclosure section not detected

**Fix**: Strengthen POSITIVE signals:
```markdown
2. In "AI Disclosure" section: The presence of this section title indicates
   AI was likely used. Phrases like "Used for X", "Helped with Y" imply
   AI tool usage even without explicit tool name.
```

### Issue 3: Low Confidence Scores

**Problem**: LLM returns 0.5 confidence even for clear cases

**Fix**: Add confidence guidelines:
```markdown
## Confidence Guidelines
- 0.9-1.0: Explicit tool mention or "Generated with X" signature
- 0.7-0.9: Clear AI disclosure section with usage statement
- 0.5-0.7: Ambiguous - implicit usage or uncertain context
- 0.0-0.5: Likely not AI-assisted, or explicit denial
```

---

## Prompt Templates by Use Case

### Template: High Precision (Minimize False Positives)

```markdown
## Detection Rules

ONLY flag as AI-assisted if you find EXPLICIT evidence:
1. Named tool mention: "Cursor", "Claude Code", "Copilot", etc.
2. "Generated with" or "Written by" + AI tool name
3. Co-Authored-By with AI domain (@anthropic.com, @cursor.sh)

Do NOT flag:
- Vague mentions like "AI helped"
- Product integrations ("Add Gemini API")
- Historical references ("Devin's PR")

When uncertain, return is_ai_assisted: false
```

### Template: High Recall (Catch All AI Usage)

```markdown
## Detection Rules

Flag as AI-assisted if ANY of these apply:
1. Any AI tool name appears (Cursor, Claude, Copilot, Cody, Aider, Devin, etc.)
2. "AI Disclosure" section exists with any content except explicit denial
3. Phrases: "AI", "LLM", "generated", "assisted", "helped", "used for"
4. Co-Authored-By patterns

Only return false if:
- Explicit denial: "No AI", "None", "N/A"
- Clearly about AI as product feature
```

---

## Response Schema

All prompts must request this JSON structure:

```json
{
  "is_ai_assisted": true,
  "tools": ["cursor", "claude"],
  "usage_category": "assisted",
  "confidence": 0.85,
  "reasoning": "AI Disclosure section mentions Cursor with Claude model"
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `is_ai_assisted` | boolean | Yes | Primary detection result |
| `tools` | string[] | Yes | Lowercase tool names detected |
| `usage_category` | string\|null | No | How AI was used |
| `confidence` | float | Yes | 0.0-1.0 confidence score |
| `reasoning` | string | No | Brief explanation |

### Tool Name Normalization

Always use lowercase, standardized names:

| Raw Text | Normalized |
|----------|------------|
| "Cursor IDE", "Cursor AI" | `cursor` |
| "Claude Code", "Claude", "Sonnet" | `claude` |
| "GitHub Copilot", "Copilot" | `copilot` |
| "Cody", "Sourcegraph Cody" | `cody` |
| "Devin AI", "Devin" | `devin` |
| "Gemini" | `gemini` |
| "ChatGPT", "GPT-4" | `chatgpt` |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-24 | Claude | Initial runbook |
