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
