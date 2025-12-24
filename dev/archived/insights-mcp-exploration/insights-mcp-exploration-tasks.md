# Phase 3: MCP Exploration - Tasks

**Last Updated:** 2025-12-21

## Task Checklist

### 1. Setup & Dependencies [S]
- [ ] Add `mcp` to `pyproject.toml`
- [ ] Run `uv sync`
- [ ] Create basic MCP server skeleton
- [ ] Verify Django integration works

**Acceptance:** MCP server starts without errors

---

### 2. Implement Core Tools [M]
- [ ] `get_team_metrics` tool
- [ ] `get_ai_trends` tool
- [ ] `get_developer_stats` tool
- [ ] `get_quality_comparison` tool
- [ ] `get_reviewer_info` tool
- [ ] `get_recent_prs` tool
- [ ] Write tool tests

**Acceptance:** All 6 tools work when called

---

### 3. Test with Claude Code [S]
- [ ] Create `.claude/mcp.json` config
- [ ] Start MCP server
- [ ] Test tool discovery
- [ ] Test tool execution
- [ ] Document any issues

**Acceptance:** Can query tformance data via Claude Code

---

### 4. Test with Gemini MCP Client [M]
- [ ] Implement Gemini MCP client wrapper
- [ ] Test tool discovery
- [ ] Test tool execution
- [ ] Compare to direct function calling
- [ ] Document differences

**Acceptance:** Gemini can use MCP tools (or documented as not working)

---

### 5. Comparison Evaluation [S]
- [ ] Run same 10 test queries via function calling
- [ ] Run same 10 test queries via MCP
- [ ] Measure: response quality, latency, complexity
- [ ] Document findings
- [ ] Make recommendation

**Acceptance:** Clear comparison documented

---

### 6. Production Considerations [S]
- [ ] Document HTTP transport setup
- [ ] Document auth strategy
- [ ] Document scaling considerations
- [ ] Create decision document

**Acceptance:** Clear path to production if MCP chosen

---

## Progress Summary

| Task | Status | Effort |
|------|--------|--------|
| 1. Setup & Dependencies | ⬜ Not Started | S |
| 2. Implement Core Tools | ⬜ Not Started | M |
| 3. Test with Claude Code | ⬜ Not Started | S |
| 4. Test with Gemini MCP | ⬜ Not Started | M |
| 5. Comparison Evaluation | ⬜ Not Started | S |
| 6. Production Considerations | ⬜ Not Started | S |

**Total Effort:** ~2 days

## Dependencies

```
Phase 2 Complete (function calling working)
    ↓
1. Setup & Dependencies
    ↓
2. Implement Core Tools
    ↓
3. Test with Claude Code ──┬── 4. Test with Gemini MCP
                           │
                           ↓
                     5. Comparison Evaluation
                           ↓
                     6. Production Considerations
```

## Test Queries for Comparison

Same queries as Phase 2:
1. "Give me a summary of how the team is doing"
2. "How is Alice performing compared to the team?"
3. "What's our AI adoption trend?"
4. "Who reviews the most PRs?"
5. "Are there any concerning patterns I should know about?"

Plus MCP-specific:
6. "What tools are available?" (tool discovery)
7. "Get metrics for the last 7 days" (parameter handling)
8. "Compare this week to last week" (multi-tool)

## Evaluation Criteria

| Criteria | Weight | Notes |
|----------|--------|-------|
| Response quality | 30% | Same as function calling? |
| Latency | 20% | Acceptable for UX? |
| Code complexity | 20% | More/less than FC? |
| Future flexibility | 15% | Multi-LLM benefit |
| Maintenance burden | 15% | Two implementations? |

## Expected Outcome

One of:
1. **Adopt MCP** - Replace function calling
2. **Keep Function Calling** - MCP not worth it
3. **Hybrid** - MCP for Claude Code, FC for web
