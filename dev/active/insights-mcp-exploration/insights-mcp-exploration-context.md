# Phase 3: MCP Exploration - Context

**Last Updated:** 2025-12-21

## Key Resources

### MCP Documentation
- Official: https://modelcontextprotocol.io/
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Building servers: https://modelcontextprotocol.io/docs/develop/build-server

### Dependencies

```toml
# pyproject.toml
[project.dependencies]
mcp = "^2.0.0"
```

## MCP Concepts

### Tools
Functions the LLM can call:
```python
@mcp.tool()
def get_team_metrics(team_slug: str) -> dict:
    """Docstring becomes the tool description."""
    pass
```

### Resources
Data the LLM can read (like GET endpoints):
```python
@mcp.resource("team://{team_slug}/metrics")
def team_metrics_resource(team_slug: str) -> str:
    """Return team metrics as text."""
    pass
```

### Prompts
Pre-defined prompt templates:
```python
@mcp.prompt()
def weekly_summary() -> str:
    """Generate a weekly summary prompt."""
    return "Summarize the team's performance this week..."
```

## FastMCP Pattern

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("server-name")

@mcp.tool()
def my_tool(arg: str) -> dict:
    """Tool description from docstring."""
    return {"result": arg}

if __name__ == "__main__":
    mcp.run()  # Runs with stdio transport
```

## Django Integration Challenges

1. **Django ORM** - MCP server needs Django settings loaded
2. **Team Context** - Must pass team_slug to all tools
3. **Auth** - MCP doesn't have built-in auth (handle at transport level)

### Solution: Django Setup in MCP Server

```python
# apps/insights/mcp_server.py
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tformance.settings")
django.setup()

from mcp.server.fastmcp import FastMCP
from apps.teams.models import Team
# ... rest of implementation
```

## Transport Options

| Transport | Use Case | Complexity |
|-----------|----------|------------|
| stdio | Local testing, Claude Code | Low |
| SSE | Web integration | Medium |
| HTTP | Production API | Medium |

## Gemini MCP Support

Gemini has **experimental** MCP support:
```python
from google import genai

# Connect to MCP server
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(tools=[session]),
        )
```

## Claude Code Integration

Add to project's `.claude/mcp.json`:
```json
{
  "mcpServers": {
    "tformance": {
      "command": ".venv/bin/python",
      "args": ["-m", "apps.insights.mcp_server"],
      "cwd": "/Users/yanchuk/Documents/GitHub/tformance"
    }
  }
}
```

## Decisions to Make

1. **Transport choice** - stdio for MVP, HTTP for production?
2. **Tool granularity** - Many specific tools or few flexible ones?
3. **Resource exposure** - Also expose resources or tools only?
4. **Auth strategy** - Team context via parameter or session?
