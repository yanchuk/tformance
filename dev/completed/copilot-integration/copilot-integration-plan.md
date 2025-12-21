# Copilot Integration Implementation Plan

**Last Updated: 2025-12-18**

## Executive Summary

Implement GitHub Copilot metrics integration to provide teams with API-based AI usage data. This complements the existing survey-based AI tracking by pulling actual Copilot usage statistics from GitHub's API for organizations with 5+ Copilot licenses.

## Current State Analysis

### Existing Infrastructure
- **GitHub OAuth**: Already implemented with `read:org` scope
- **AIUsageDaily Model**: Exists with `copilot` source option, ready to store metrics
- **Integration Patterns**: Well-established patterns in `apps/integrations/` for OAuth, sync tasks, and services

### Gaps to Address
1. No Copilot-specific API integration
2. OAuth scope needs `manage_billing:copilot` for Copilot metrics access
3. No UI to display Copilot metrics on dashboard
4. No sync task for pulling Copilot data

## Proposed Future State

Teams with GitHub Copilot will see:
- Daily/weekly Copilot usage metrics per team member
- Acceptance rates and active hours
- IDE breakdown (VS Code, JetBrains, etc.)
- Correlation with delivery metrics on existing dashboards

## API Integration Details

### GitHub Copilot Metrics API

**Endpoint**: `GET /orgs/{org}/copilot/metrics`

**Required Scopes** (need to add):
- `manage_billing:copilot` OR `read:org` (already have read:org)

**Key Response Fields**:
- `date` - YYYY-MM-DD format
- `total_active_users` - Users with any Copilot activity
- `total_engaged_users` - Users who actively interacted
- `copilot_ide_code_completions` - Suggestions shown/accepted by language/editor

**Restrictions**:
- Requires 5+ active Copilot licenses on that day
- Returns up to 100 days historical data
- Metrics processed once daily for previous day

## Implementation Phases

### Phase 1: OAuth Scope Update (S)
Update GitHub OAuth to request `manage_billing:copilot` scope for teams that want Copilot metrics.

### Phase 2: Copilot Service Module (M)
Create `apps/integrations/services/copilot_metrics.py` with:
- API client for Copilot metrics endpoint
- Response parsing and normalization
- Error handling for 5+ license requirement

### Phase 3: Data Storage (S)
Extend `AIUsageDaily` model usage for Copilot data:
- Map API response to existing fields
- Add any missing fields if needed

### Phase 4: Sync Task (M)
Create Celery task `sync_copilot_metrics`:
- Daily sync of Copilot metrics
- Retry logic for API failures
- Team member matching by GitHub username

### Phase 5: Dashboard Enhancement (M)
Add Copilot metrics to existing dashboards:
- AI adoption chart with Copilot data
- Per-developer Copilot usage
- Acceptance rate trends

### Phase 6: Settings UI (S)
Add toggle in team settings:
- Enable/disable Copilot sync
- Re-authorize with Copilot scope if needed

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Org has <5 Copilot licenses | High | Medium | Graceful "not available" state |
| API rate limits | Low | Low | Respect limits, cache results |
| User matching failures | Medium | Medium | Fall back to aggregate data |
| OAuth scope rejection | Medium | Low | Optional feature, clear messaging |

## Success Metrics

1. Teams with Copilot see usage data within 24h of enabling
2. 90%+ of Copilot users matched to TeamMember records
3. Dashboard loads Copilot data in <2s
4. Zero data sync failures due to API errors (after retries)

## Dependencies

- GitHub OAuth integration (Phase 2) - DONE
- AIUsageDaily model (Phase 1) - DONE
- Celery task infrastructure - DONE
- Dashboard charting (Phase 4) - DONE

## Estimated Effort

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| 1. OAuth Scope | S (2h) | None |
| 2. Service Module | M (4h) | Phase 1 |
| 3. Data Storage | S (1h) | Phase 2 |
| 4. Sync Task | M (4h) | Phases 2-3 |
| 5. Dashboard | M (6h) | Phase 4 |
| 6. Settings UI | S (2h) | Phases 1-4 |

**Total**: ~19 hours of development

## Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub Copilot API                    │
│            GET /orgs/{org}/copilot/metrics              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              copilot_metrics.py (Service)                │
│  - fetch_copilot_metrics(org, token)                    │
│  - parse_metrics_response(data)                         │
│  - check_copilot_availability(org, token)               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              tasks.py (Celery Task)                      │
│  - sync_copilot_metrics_task(team_id)                   │
│  - sync_all_copilot_metrics() [daily scheduler]         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    AIUsageDaily Model                    │
│  source='copilot', member, date, suggestions_*          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Dashboard Charts                        │
│  - AI Adoption trend (includes Copilot data)            │
│  - Per-member Copilot metrics table                     │
└─────────────────────────────────────────────────────────┘
```
