# Phase 3: MCP Server Exploration

**Last Updated:** 2025-12-21

## Executive Summary

Evaluate Model Context Protocol (MCP) as an alternative to direct function calling. MCP provides a standardized interface that works across different LLMs (Claude, Gemini, OpenAI) and enables tool reuse.

## Prerequisites

- **Phase 2 Complete** - Function calling working
- **Comparison Data** - Know what works/doesn't with function calling

## Goals

1. **Evaluate MCP Benefits** - Is the abstraction worth it?
2. **Build MCP Server** - Expose tformance data via MCP
3. **Test with Multiple LLMs** - Claude, Gemini
4. **Compare to Function Calling** - Quality, latency, complexity

## Why Consider MCP?

| Benefit | Description |
|---------|-------------|
| **LLM Agnostic** | Same tools work with Claude, Gemini, OpenAI |
| **Claude Code Native** | Already using Claude Code for development |
| **Tool Discovery** | LLMs can discover available tools automatically |
| **Reusable** | Same server works for UI, CLI, IDE |
| **Open Standard** | Anthropic + OpenAI + Google backing |

## Architecture Options

### Option A: Stdio Transport (Simple)
```
Django App → subprocess → MCP Server (Python) → dashboard_service.py
```
- Pro: Simple setup, same process
- Con: Only works within same machine

### Option B: HTTP/SSE Transport (Production)
```
Django App → HTTP → MCP Server (FastAPI) → dashboard_service.py
```
- Pro: Works across network, scalable
- Con: More infrastructure

### Option C: Embedded (FastMCP in Django)
```
Django View → FastMCP → dashboard_service.py
```
- Pro: No separate process
- Con: Experimental pattern

## MCP Server Implementation

```python
# apps/insights/mcp_server.py
from mcp.server.fastmcp import FastMCP
from apps.metrics.services.dashboard_service import (
    get_key_metrics, get_ai_adoption_trend, get_team_breakdown
)
from apps.teams.models import Team
from datetime import datetime

mcp = FastMCP("tformance-insights")

@mcp.tool()
def get_team_metrics(team_slug: str, days: int = 30) -> dict:
    """Get key metrics for a team.

    Args:
        team_slug: Team identifier (e.g., 'acme-corp')
        days: Number of days to look back (default 30)

    Returns:
        Dictionary with prs_merged, avg_cycle_time, avg_quality_rating, ai_assisted_pct
    """
    team = Team.objects.get(slug=team_slug)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    return get_key_metrics(team, start_date, end_date)

@mcp.tool()
def get_ai_trends(team_slug: str, weeks: int = 4) -> list:
    """Get AI adoption trend by week.

    Args:
        team_slug: Team identifier
        weeks: Number of weeks to include

    Returns:
        List of {week, value} dictionaries showing AI adoption percentage
    """
    team = Team.objects.get(slug=team_slug)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks)
    return get_ai_adoption_trend(team, start_date, end_date)

@mcp.tool()
def get_developer_stats(team_slug: str, days: int = 30) -> list:
    """Get per-developer metrics.

    Args:
        team_slug: Team identifier
        days: Number of days to look back

    Returns:
        List of developer stats with prs_merged, avg_cycle_time, ai_pct
    """
    team = Team.objects.get(slug=team_slug)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    return get_team_breakdown(team, start_date, end_date)

# More tools...
```

## Running the MCP Server

```bash
# As standalone (for testing with Claude Code)
python -m apps.insights.mcp_server

# Via stdio transport
python -c "from apps.insights.mcp_server import mcp; mcp.run()"
```

## Testing with Claude Code

Add to `.claude/mcp.json`:
```json
{
  "mcpServers": {
    "tformance": {
      "command": "python",
      "args": ["-m", "apps.insights.mcp_server"],
      "cwd": "/path/to/tformance"
    }
  }
}
```

Then in Claude Code:
```
> What metrics are available for acme-corp team?
> How is Alice performing compared to the team average?
```

## Comparison Metrics

| Metric | Function Calling | MCP |
|--------|-----------------|-----|
| Setup time | 2 hours | 4 hours |
| Lines of code | ~200 | ~300 |
| LLM compatibility | 1 (Gemini) | 3+ |
| Testing ease | Unit tests | Integration tests |
| Claude Code support | No | Native |
| Debugging | Simple | Extra layer |

## Decision Framework

**Stick with Function Calling if:**
- Single LLM (Gemini) is sufficient
- Simpler codebase preferred
- No Claude Code integration needed

**Switch to MCP if:**
- Multi-LLM support desired
- Claude Code integration valuable
- Building tools for broader use
- Future-proofing is priority

## Files to Create

```
apps/insights/
├── mcp_server.py           # MCP server definition
├── mcp_tools.py            # Tool implementations
├── tests/
│   └── test_mcp_server.py

scripts/
└── run_mcp_server.py       # Standalone runner
```
