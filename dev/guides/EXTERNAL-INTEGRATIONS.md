# External Integrations Guide

> Back to [CLAUDE.md](../../CLAUDE.md)

**Always prefer official SDKs/libraries over direct API calls.**

## Library Selection Hierarchy

1. **Official SDK/library** - Published and maintained by service provider
2. **Well-maintained 3rd party library** - Popular, actively maintained, good docs
3. **Direct API calls** - Last resort when no suitable library exists

## Required Libraries

| Service | Library | PyPI Package | Notes |
|---------|---------|--------------|-------|
| GitHub | PyGithub | `PyGithub` | Official community library, most popular |
| Jira | jira-python | `jira` | Most popular, well-maintained |
| Slack | slack-sdk | `slack-sdk` | Official Slack SDK |
| Atlassian | atlassian-python-api | `atlassian-python-api` | Alternative for Jira/Confluence |

## Documentation Lookup with Context7

**Always use Context7 MCP server to get up-to-date documentation** before implementing integrations:

```
# 1. Resolve the library ID
mcp__context7__resolve-library-id(libraryName="PyGithub")

# 2. Fetch relevant documentation
mcp__context7__get-library-docs(context7CompatibleLibraryID="/...", topic="pull requests")
```

This ensures current API methods and best practices, not outdated patterns.

## Why Libraries Over Direct API

- **Pagination handling** - Automatic cursor-based and offset pagination
- **Rate limiting** - Built-in retry logic and rate limit respect
- **Authentication** - Proper token refresh, OAuth flows handled
- **Error handling** - Typed exceptions, clear error messages
- **Type safety** - Many have type hints or stubs available
- **Testing** - Easier to mock library objects than raw HTTP responses

## Integration Code Organization

- Integration-specific code lives in `apps/integrations/`
- Instantiate clients with tokens from team's connected accounts
- Use dependency injection patterns for testability
- Wrap library calls in service classes for domain logic

## GitHub Sync Module Structure

The GitHub sync functionality is organized as a modular package at `apps/integrations/services/github_sync/`:

| Module | Purpose |
|--------|---------|
| `client.py` | GitHub API client functions (PyGithub wrappers) |
| `converters.py` | Transform PyGithub objects to dictionaries |
| `processors.py` | Per-entity sync operations (reviews, commits, files, etc.) |
| `metrics.py` | Calculate iteration metrics and correlations |
| `sync.py` | Sync orchestration (history, incremental) |
| `__init__.py` | Re-exports all public functions |

**Usage (backward compatible):**
```python
from apps.integrations.services.github_sync import (
    sync_repository_history,
    sync_repository_incremental,
    get_repository_pull_requests,
)
```

**When mocking in tests**, patch where the name is looked up:
```python
# Correct: patch in sync.py where it's imported
@patch("apps.integrations.services.github_sync.sync.get_repository_pull_requests")

# Wrong: patching the facade doesn't affect sync.py's import
@patch("apps.integrations.services.github_sync.get_repository_pull_requests")
```

## GitHub GraphQL API

For bulk operations (many PRs, commits, files), use the GraphQL client:

```python
from apps.integrations.services.github_graphql import GitHubGraphQLClient
from apps.integrations.services.github_graphql_sync import (
    sync_repository_history_graphql,
    sync_repository_incremental_graphql,
)
```
