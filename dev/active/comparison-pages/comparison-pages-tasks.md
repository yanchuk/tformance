# Comparison Pages: Tasks

Last Updated: 2026-01-24

## Phase 1: Tests (TDD Retrofit)

- [ ] **T1.1** Create `apps/web/tests/test_compare.py`
- [ ] **T1.2** Test `get_competitor()` returns correct data for valid slug
- [ ] **T1.3** Test `get_competitor()` returns None for invalid slug
- [ ] **T1.4** Test `calculate_savings()` returns correct savings for 50-dev team vs LinearB
- [ ] **T1.5** Test `calculate_savings()` returns None for competitor with no pricing
- [ ] **T1.6** Test `get_feature_status_display()` returns correct icons
- [ ] **T1.7** Test `compare_hub` view returns 200
- [ ] **T1.8** Test `compare_hub` view context contains all 7 competitors
- [ ] **T1.9** Test `compare_competitor` view returns 200 for valid slug
- [ ] **T1.10** Test `compare_competitor` view returns 404 for invalid slug
- [ ] **T1.11** Test `compare_competitor` view context contains savings_table
- [ ] **T1.12** Test `ComparisonSitemap.items()` returns 8 items (hub + 7 competitors)
- [ ] **T1.13** Test `ComparisonSitemap.location()` returns correct URLs
- [ ] **T1.14** Run full test suite: `.venv/bin/pytest apps/web/tests/test_compare.py -v`

## Phase 2: Commit & Verify

- [ ] **T2.1** Run full test suite: `make test`
- [ ] **T2.2** Stage all comparison files: `git add apps/web/compare_data.py apps/web/sitemaps.py apps/web/urls.py apps/web/views.py apps/web/templatetags/number_filters.py templates/web/compare/ tformance/urls.py`
- [ ] **T2.3** Commit with message: `feat(web): add competitor comparison pages with sitemap`
- [ ] **T2.4** Start dev server: `make dev`
- [ ] **T2.5** Verify `/compare/` loads
- [ ] **T2.6** Verify `/compare/linearb/` loads
- [ ] **T2.7** Verify `/compare/jellyfish/` loads
- [ ] **T2.8** Verify `/sitemap.xml` includes comparison section
- [ ] **T2.9** Check browser console for JS errors

## Phase 3: Deploy

- [ ] **T3.1** Push branch: `git push origin feature/comparison-pages`
- [ ] **T3.2** Create PR or merge to main
- [ ] **T3.3** Verify on staging/production
- [ ] **T3.4** Submit sitemap to Google Search Console (optional)

---

## Quick Commands

```bash
# Run comparison tests only
.venv/bin/pytest apps/web/tests/test_compare.py -v

# Verify sitemap in shell
.venv/bin/python manage.py shell -c "
from apps.web.sitemaps import ComparisonSitemap
print(list(ComparisonSitemap().items()))
"

# Stage comparison files
git add apps/web/compare_data.py apps/web/sitemaps.py apps/web/urls.py apps/web/views.py apps/web/templatetags/number_filters.py templates/web/compare/ tformance/urls.py templates/web/components/footer.html templates/llms.txt

# Commit
git commit -m "feat(web): add competitor comparison pages with sitemap"
```
