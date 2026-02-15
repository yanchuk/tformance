---
name: chart-patterns
description: Chart.js patterns for Tformance dashboards. Triggers on Chart.js, chart, graph, visualization, dashboard chart, bar chart, line chart, doughnut chart. Easy Eyes theme colors and responsive patterns.
---

# Chart.js Patterns

## Purpose

Consistent Chart.js implementations following the Easy Eyes Dashboard design system.

## When to Use

**Automatically activates when:**
- Creating dashboard charts
- Working with Chart.js configuration
- Building visualizations for metrics

## Theme Colors

Use DaisyUI semantic colors that adapt to theme:

```javascript
// Get CSS custom property values
const getColor = (varName) =>
  getComputedStyle(document.documentElement).getPropertyValue(varName).trim();

const colors = {
  primary: getColor('--p'),      // Coral orange
  secondary: getColor('--s'),    // Golden amber
  accent: getColor('--a'),       // Teal
  success: getColor('--su'),     // Green
  warning: getColor('--wa'),     // Amber
  error: getColor('--er'),       // Red
  neutral: getColor('--n'),      // Gray
  base100: getColor('--b1'),     // Background
  baseContent: getColor('--bc'), // Text
};
```

## Chart Configuration Patterns

### Bar Chart (PR Metrics)

```javascript
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
    datasets: [{
      label: 'PRs Merged',
      data: [12, 19, 8, 15],
      backgroundColor: 'oklch(var(--p))',
      borderRadius: 4,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: 'oklch(var(--bc))' }
      }
    },
    scales: {
      x: {
        ticks: { color: 'oklch(var(--bc) / 0.7)' },
        grid: { color: 'oklch(var(--bc) / 0.1)' }
      },
      y: {
        ticks: { color: 'oklch(var(--bc) / 0.7)' },
        grid: { color: 'oklch(var(--bc) / 0.1)' }
      }
    }
  }
});
```

### Line Chart (Trends)

```javascript
new Chart(ctx, {
  type: 'line',
  data: {
    labels: weeks,
    datasets: [{
      label: 'AI-Assisted',
      data: aiData,
      borderColor: 'oklch(var(--p))',
      backgroundColor: 'oklch(var(--p) / 0.1)',
      fill: true,
      tension: 0.3,
    }, {
      label: 'Non-AI',
      data: nonAiData,
      borderColor: 'oklch(var(--a))',
      backgroundColor: 'transparent',
      tension: 0.3,
    }]
  },
  options: {
    responsive: true,
    interaction: {
      intersect: false,
      mode: 'index',
    },
    plugins: {
      tooltip: {
        backgroundColor: 'oklch(var(--b2))',
        titleColor: 'oklch(var(--bc))',
        bodyColor: 'oklch(var(--bc) / 0.8)',
        borderColor: 'oklch(var(--bc) / 0.2)',
        borderWidth: 1,
      }
    }
  }
});
```

### Doughnut Chart (Distribution)

```javascript
new Chart(ctx, {
  type: 'doughnut',
  data: {
    labels: ['Copilot', 'Cursor', 'Claude', 'Other'],
    datasets: [{
      data: [45, 30, 15, 10],
      backgroundColor: [
        'oklch(var(--p))',      // Primary
        'oklch(var(--a))',      // Accent
        'oklch(var(--s))',      // Secondary
        'oklch(var(--n))',      // Neutral
      ],
      borderWidth: 0,
    }]
  },
  options: {
    responsive: true,
    cutout: '60%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: 'oklch(var(--bc))' }
      }
    }
  }
});
```

## HTMX Integration Pattern

### Template Structure

```html
<!-- Chart container with HTMX refresh -->
<div class="app-card"
     hx-get="{% url 'metrics:chart_data' team.slug %}"
     hx-trigger="load, every 60s"
     hx-swap="innerHTML">
  <canvas id="myChart" class="h-64"></canvas>
</div>
```

### Partial Template (returned by HTMX)

```html
<canvas id="myChart" class="h-64"></canvas>
<script>
  (function() {
    const ctx = document.getElementById('myChart');
    new Chart(ctx, {{ chart_config|safe }});
  })();
</script>
```

### View Pattern

```python
def chart_data_view(request, team_slug):
    service = DashboardService(team)
    data = service.get_chart_data()

    chart_config = {
        'type': 'bar',
        'data': {
            'labels': data['labels'],
            'datasets': [{
                'label': 'PRs',
                'data': data['values'],
            }]
        }
    }

    return render(request, 'partials/chart.html', {
        'chart_config': json.dumps(chart_config)
    })
```

## Responsive Sizing

```html
<!-- Fixed height container -->
<div class="h-64 w-full">
  <canvas id="chart"></canvas>
</div>

<!-- Aspect ratio container -->
<div class="aspect-video w-full">
  <canvas id="chart"></canvas>
</div>
```

## Common Chart Types in Tformance

| Chart | Use For | Type |
|-------|---------|------|
| Weekly PRs | Throughput trend | Line |
| AI Tool Distribution | Tool breakdown | Doughnut |
| Cycle Time Comparison | AI vs Non-AI | Bar (grouped) |
| Developer Activity | Per-person metrics | Horizontal Bar |
| Tech Categories | Category breakdown | Doughnut |

## Color Palette Reference

| Use | Color Variable | Notes |
|-----|---------------|-------|
| Primary data | `--p` | Coral orange |
| Secondary data | `--a` | Teal accent |
| Tertiary data | `--s` | Golden amber |
| Positive trend | `--su` | Success green |
| Negative trend | `--er` | Error red |
| Neutral/other | `--n` | Gray |
| Grid lines | `--bc / 0.1` | Very subtle |
| Text | `--bc` | Base content |

---

**Enforcement Level**: SUGGEST
**Priority**: Low
