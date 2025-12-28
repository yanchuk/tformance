# Context: Pegasus Boilerplate Removal

**Last Updated: 2025-12-28**

## Key Files to Modify

| File | Changes Required |
|------|------------------|
| `tformance/settings.py` | Remove PEGASUS_APPS, teams_example from PROJECT_APPS, test-celerybeat task |
| `tformance/urls.py` | Remove 3 URL patterns (lines 55, 74-75) |

## Directories to Delete

```
pegasus/                          # Entire directory
apps/teams_example/               # Entire directory
templates/pegasus/                # Entire directory
templates/teams_example/          # Entire directory
assets/javascript/pegasus/        # Entire directory
assets/styles/pegasus/            # If exists
static/images/pegasus/            # If exists
pegasus-config.yaml               # Root config file
```

## Key Decisions

1. **Full removal vs partial**: Full removal chosen - no business value in keeping any part
2. **Database migration**: Not needed - models are self-contained in removed apps
3. **Git history**: Preserved in git, no need to rewrite history

## Dependencies

- None identified - boilerplate is isolated from production code

## Verification Commands

```bash
# After removal
make test                    # Full test suite
make dev                     # Start dev server
grep -r "pegasus" apps/      # Should return nothing
grep -r "teams_example" apps/ --include="*.py" | grep -v __pycache__  # Should only show removal
```

## Related PRD Sections

- N/A - This is cleanup, not feature work
