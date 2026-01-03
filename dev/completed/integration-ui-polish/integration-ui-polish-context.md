# Integration Page UI Polish - Context

**Last Updated:** 2026-01-03

---

## Critical Files

| File | Purpose |
|------|---------|
| `apps/integrations/templates/integrations/home.html` | Main template - all changes here |
| `apps/integrations/services/integration_flags.py` | IntegrationStatus dataclass, benefits data |
| `tests/e2e/integration-flags.spec.ts` | E2E tests for integration flags |
| `assets/styles/app/tailwind/design-system.css` | Badge styling (app-badge-*) |

---

## Key Code Patterns

### Coming Soon Card Pattern (from Jira)
```html
{% if not jira_status.enabled %}
  <!-- Coming Soon badge -->
  <span class="app-badge app-badge-warning">Coming Soon</span>

  <!-- Benefits list -->
  <ul class="space-y-3 mt-4 text-base-content/80">
    {% for benefit in jira_status.benefits %}
    <li class="flex items-start gap-3">
      <svg class="w-5 h-5 text-success shrink-0 mt-0.5">...</svg>
      <div>
        <span class="font-medium text-base-content">{{ benefit.title }}</span>
        <p class="text-sm text-base-content/70">{{ benefit.description }}</p>
      </div>
    </li>
    {% endfor %}
  </ul>

  <!-- I'm Interested button -->
  <button hx-post="{% url 'integrations:track_interest' %}?integration=jira"
          hx-swap="outerHTML"
          class="btn btn-outline btn-primary">
    I'm Interested
  </button>
{% endif %}
```

### HTMX Interest Tracking Response
```html
<!-- partials/interest_confirmed.html -->
<button class="btn btn-ghost btn-disabled" disabled>
  <svg>✓</svg> Thanks!
</button>
```

---

## Benefits Data (from integration_flags.py)

### Copilot Benefits (lines 48-67)
```python
{
    "title": "Acceptance rate",
    "description": "Track how often suggestions are accepted"
},
{
    "title": "Lines of code",
    "description": "Measure AI-generated code volume"
},
{
    "title": "Time savings",
    "description": "Estimate productivity gains from AI"
}
```

### Slack Benefits (lines 68-87)
```python
{
    "title": "PR surveys via DM",
    "description": "Quick 1-click surveys to capture AI-assisted PRs"
},
{
    "title": "Weekly leaderboards",
    "description": "Gamified AI Detective rankings"
},
{
    "title": "Higher response rates",
    "description": "Meet developers where they work"
}
```

---

## Context Variables Available in Template

From `integrations_home` view:
- `jira_status` - IntegrationStatus for Jira
- `slack_status` - IntegrationStatus for Slack
- `copilot_status` - IntegrationStatus for Copilot
- `google_status` - IntegrationStatus for Google Workspace

Each status has:
- `.enabled` - bool (feature flag state)
- `.coming_soon` - bool
- `.benefits` - list of {title, description}
- `.name`, `.slug`, `.icon_color`, `.description`

---

## E2E Test Patterns (from existing tests)

```typescript
// Card selection
const slackCard = page.locator('.app-card').filter({ hasText: 'Slack' });

// Badge check
await expect(slackCard.getByText('Coming Soon')).toBeVisible();

// Benefits check
await expect(slackCard.getByText('PR surveys via DM')).toBeVisible();

// Button check
await expect(slackCard.getByRole('button', { name: "I'm Interested" })).toBeVisible();
```

---

## Decisions Made

1. **Icon backgrounds**: Remove completely (not replace with different bg)
2. **Badge styling**: Use `badge badge-warning` for better contrast
3. **Google icon**: Use `fa-brands fa-google` from FontAwesome
4. **Benefits format**: Same 3-item bullet list as Jira/Google
