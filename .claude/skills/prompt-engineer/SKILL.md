---
name: prompt-engineer
description: Prompt engineering best practices for LLM prompts. Triggers on prompt engineering, LLM prompts, system prompts, prompt optimization, prompt templates, few-shot learning, prompt design, prompt iteration, user prompts, assistant responses, Groq, LiteLLM, prompt tuning, prompt testing, eval prompts. Covers GPT and reasoning model differences, message roles, prompt structure, and industry best practices from OpenAI and Anthropic.
---

# Prompt Engineering Best Practices

## Purpose

Guide developers in writing effective LLM prompts following industry best practices from OpenAI and Anthropic. This skill helps optimize prompts for clarity, consistency, and performance.

## When to Use This Skill

Automatically activates when:
- Creating or modifying LLM prompts (system prompts, user prompts)
- Working with prompt templates (Jinja2, string formatting)
- Implementing few-shot learning examples
- Optimizing prompt performance
- Building AI-powered features
- Working with Groq, LiteLLM, or other LLM providers
- Testing and evaluating prompts (promptfoo, evals)

## Quick Reference

### Prompt Structure Order (Optimized for Caching)

```
1. IDENTITY      → Role, purpose, communication style (static)
2. INSTRUCTIONS  → Rules, constraints, what to do/never do (static)
3. EXAMPLES      → Few-shot learning pairs (semi-static)
4. CONTEXT       → Dynamic data, documents (changes per request)
```

**Why this order?** Prompt caching works best when static content comes first. Dynamic content at the end maximizes cache hits.

### Message Roles Priority

| Role | Priority | Purpose | Analogy |
|------|----------|---------|---------|
| `developer`/`system` | Highest | Business logic, rules | Function definition |
| `user` | Medium | Inputs, configuration | Function arguments |
| `assistant` | - | Model responses | Return values |

---

## Prompt Structure Deep Dive

### 1. Identity Section

Define who the model is and how it should communicate.

```markdown
# Identity

You are an expert code reviewer specializing in Python and Django.
You communicate clearly and concisely, focusing on actionable feedback.
You prioritize security issues, then correctness, then style.
```

**Best Practices:**
- Be specific about expertise and domain
- Define communication style upfront
- State priorities when multiple concerns exist

### 2. Instructions Section

Explicit rules and constraints for behavior.

```markdown
# Instructions

## What to Do
- Analyze code for security vulnerabilities
- Check for Django best practices
- Provide specific line references

## What NOT to Do
- Do not suggest complete rewrites
- Do not comment on formatting (handled by linters)
- Do not make assumptions about business logic
```

**Best Practices:**
- Use "Do not" for constraints (clearer than "Avoid")
- Group related instructions
- Be explicit about edge cases

### 3. Examples Section (Few-Shot Learning)

Show diverse input/output pairs to guide behavior.

```markdown
# Examples

<user_query id="example-1">
Review this function for security issues:
def get_user(user_id):
    return User.objects.get(id=user_id)
</user_query>

<assistant_response id="example-1">
**Security Issue (Line 2):** Missing permission check. Add `@login_required` decorator or verify user has access.

**Recommendation:**
```python
@login_required
def get_user(request, user_id):
    if not request.user.has_perm('view_user', user_id):
        raise PermissionDenied()
    return User.objects.get(id=user_id)
```
</assistant_response>
```

**Best Practices:**
- Show 2-5 diverse examples
- Use consistent XML/Markdown formatting
- Include edge cases in examples
- Label examples with IDs for reference

### 4. Context Section

Dynamic data specific to each request.

```markdown
# Context

<codebase_info>
Framework: Django 4.2
Python: 3.12
Key Models: Team, PullRequest, TeamMember
</codebase_info>

<code_to_review>
{{ code_snippet }}
</code_to_review>
```

**Best Practices:**
- Place at the end for caching benefits
- Use XML tags to delineate boundaries
- Include relevant metadata

---

## Formatting Guidelines

### Use Markdown for Structure

```markdown
# Main Section
## Subsection
### Details

- Bullet points for lists
- **Bold** for emphasis
- `code` for technical terms
```

### Use XML Tags for Data Boundaries

```xml
<user_input>
Content from user that needs processing
</user_input>

<context document_type="pr_diff" file_count="5">
Diff content here...
</context>
```

**XML Attributes** add metadata the model can reference:
```xml
<example id="1" category="positive">...</example>
<example id="2" category="negative">...</example>
```

---

## Model-Specific Prompting

### GPT Models (gpt-4, gpt-4o, gpt-4.1)

Think of GPT as a **junior coworker** - needs explicit instructions.

**Best Practices:**
- Provide precise, step-by-step instructions
- Be explicit about output format
- Include logic and reasoning in the prompt
- Use detailed examples

```markdown
# Instructions

Follow these steps exactly:
1. Read the code snippet
2. Identify any security vulnerabilities
3. For each vulnerability, provide:
   - Line number
   - Severity (Critical/High/Medium/Low)
   - Description
   - Recommended fix
4. Output as JSON array
```

### Reasoning Models (o1, o3, DeepSeek R1)

Think of reasoning models as a **senior coworker** - give goals, trust them.

**Best Practices:**
- Provide high-level guidance
- Let the model work out details
- Don't over-constrain the approach
- Focus on outcomes, not steps

```markdown
# Goal

Analyze this code for security issues and provide actionable recommendations.
Focus on issues that could lead to data breaches or unauthorized access.
```

### Open Source Reasoning Models (Qwen QwQ, DeepSeek R1 distills)

When using OSS models via Groq/LiteLLM:
- May need more explicit formatting instructions
- Test with your specific model version
- Consider adding "Think step by step" for complex tasks

---

## Agentic Prompts

For multi-step, autonomous tasks:

### Planning and Persistence

```markdown
# Agent Instructions

You are an autonomous agent. Continue working until the task is fully complete.

## Workflow
1. Decompose the task into subtasks
2. Execute each subtask
3. Verify completion before moving on
4. Only stop when ALL subtasks are done

## Progress Tracking
- Maintain a TODO list of remaining work
- Update status after each action
- Report blockers immediately
```

### Tool Use Guidance

```markdown
# Tool Usage

Before calling any tool:
1. State why you're calling it
2. Describe expected outcome
3. Call the tool
4. Verify the result matches expectations

## Available Tools
- `search_codebase(query)`: Find relevant code
- `read_file(path)`: Read file contents
- `edit_file(path, changes)`: Modify files
```

---

## Output Format Control

### Structured Output (JSON)

```markdown
# Output Format

Respond with valid JSON matching this schema:
{
  "issues": [
    {
      "line": <int>,
      "severity": "critical" | "high" | "medium" | "low",
      "description": <string>,
      "fix": <string>
    }
  ],
  "summary": <string>
}

Do not include any text outside the JSON object.
```

### Constrained Output

```markdown
# Response Constraints

- Maximum 3 sentences
- No markdown formatting
- No bullet points
- Plain text only
```

---

## Testing and Iteration

### Version Your Prompts

```python
# In your code
PROMPT_VERSION = "2.1.0"  # Semantic versioning

# Track changes
# v2.1.0 - Added security focus
# v2.0.0 - Restructured for caching
# v1.0.0 - Initial version
```

### Use Evals

```bash
# Export prompts for testing
make export-prompts

# Run promptfoo evaluation
npx promptfoo eval
```

### Test Diverse Inputs

Before deploying, test with:
- Happy path inputs
- Edge cases
- Adversarial inputs
- Empty/null inputs
- Very long inputs

### Pin Model Versions in Production

```python
# Good - Pinned version
model = "gpt-4.1-2025-04-14"

# Bad - Latest (behavior may change)
model = "gpt-4.1"
```

---

## Context Window Management

| Model | Context Window |
|-------|---------------|
| GPT-4 | ~128k tokens |
| GPT-4.1 | ~1M tokens |
| Claude 3.5 | ~200k tokens |
| Groq (Llama) | ~128k tokens |

**Best Practices:**
- Estimate token usage before sending
- Truncate context if needed (prioritize recent/relevant)
- Use summarization for long documents

---

## Common Pitfalls

### Avoid

1. **Vague instructions**: "Be helpful" → "Provide specific code examples"
2. **Missing constraints**: No format → Model picks random format
3. **Over-prompting**: Too many rules → Model gets confused
4. **Under-prompting reasoning models**: Too explicit → Wastes their capability
5. **Ignoring caching**: Dynamic content first → Cache misses

### Anti-Patterns

```markdown
# Bad - Vague
Be a good assistant.

# Good - Specific
You are a Django code reviewer. Focus on security and performance.
Respond with bullet points. Maximum 5 issues per review.
```

---

## Tformance-Specific Patterns

### Insight LLM Prompts

Location: `apps/metrics/prompts/templates/insight/`

```python
# Load and render templates
from apps.metrics.services.llm_prompts import build_user_prompt

prompt = build_user_prompt(
    metrics_context=metrics_data,
    template_name="user.jinja2"
)
```

### Prompt Template Changes

**Require approval before modifying:**
1. Explain the change with diff
2. Wait for user approval
3. Bump PROMPT_VERSION
4. Run `make export-prompts && npx promptfoo eval`

---

## Reference Files

- [PROMPT-ENGINEERING.md](/prd/PROMPT-ENGINEERING.md) - Project-specific prompt guidelines
- [OpenAI Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering) - OpenAI best practices
- [Claude Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering) - Anthropic guidelines

---

**Line Count:** ~300 (within 500-line rule)
