# Split Integrations Models - Context

**Last Updated:** 2026-01-10
**Status:** IN PROGRESS

## Key Files

### Source File
- `apps/integrations/models.py` (809 lines) - Will be converted to directory

### Target Files (to create)
- `apps/integrations/models/__init__.py`
- `apps/integrations/models/credentials.py`
- `apps/integrations/models/github.py`
- `apps/integrations/models/jira.py`
- `apps/integrations/models/slack.py`

### Test Files
- `apps/integrations/tests/test_models.py` (61KB) - Primary test file
- `apps/integrations/tests/test_tracked_repository.py` - TrackedRepository specific tests
- `apps/integrations/tests/test_github_app_installation.py` - GitHubAppInstallation tests

## External Imports (30+ files)

Key files that import from `apps.integrations.models`:
```python
# These will continue to work via __init__.py re-exports
from apps.integrations.models import GitHubIntegration
from apps.integrations.models import IntegrationCredential
from apps.integrations.models import TrackedRepository
from apps.integrations.models import JiraIntegration
from apps.integrations.models import SlackIntegration
from apps.integrations.models import GitHubAppInstallation
```

## Key Decisions

1. **Keep all GitHub models together** - GitHubIntegration, TrackedRepository, GitHubAppInstallation have tight coupling through ForeignKeys

2. **Credentials as separate file** - IntegrationCredential is the base for all provider integrations, clean separation

3. **No internal import changes needed** - All models currently in same file, so no cross-file imports exist

4. **Follow existing pattern** - Same pattern as `apps/metrics/models/` split (github.py → pull_requests.py)

## Critical Import Pattern

```python
# Inside models/ directory - use relative imports
from .credentials import IntegrationCredential
from .github import GitHubIntegration, TrackedRepository, GitHubAppInstallation

# Outside models/ directory - use __init__.py re-exports (unchanged)
from apps.integrations.models import GitHubIntegration  # Works unchanged
```

## Shared Constants

Models import from `apps/integrations/constants`:
```python
from apps.integrations.constants import (
    SYNC_STATUS_CHOICES,
    SYNC_STATUS_COMPLETE,
    SYNC_STATUS_ERROR,
    SYNC_STATUS_PENDING,
    SYNC_STATUS_SYNCING,
)
```

This will need to be imported in each new model file that uses these constants.

## Model Dependencies

### IntegrationCredential (credentials.py)
- BaseTeamModel
- CustomUser (for connected_by FK)
- EncryptedTextField

### GitHubIntegration (github.py)
- BaseTeamModel
- IntegrationCredential (OneToOne)

### TrackedRepository (github.py)
- BaseTeamModel
- GitHubIntegration (FK, nullable)
- GitHubAppInstallation (FK, nullable, string reference)

### GitHubAppInstallation (github.py)
- Team (FK, nullable - overrides BaseTeamModel)
- EncryptedTextField

### JiraIntegration (jira.py)
- BaseTeamModel
- IntegrationCredential (OneToOne)

### TrackedJiraProject (jira.py)
- BaseTeamModel
- JiraIntegration (FK)

### SlackIntegration (slack.py)
- BaseTeamModel
- IntegrationCredential (OneToOne)

## Factories Location

- `apps/integrations/factories.py` - Contains factories for these models
- No changes needed to factories (they import from models package)
