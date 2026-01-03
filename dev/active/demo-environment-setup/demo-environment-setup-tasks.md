# Demo Environment Setup - Tasks

**Last Updated: 2026-01-02**

## Progress Summary

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: LLM Processing | Not Started | 0/2 |
| Phase 2: Generate Insights | Not Started | 0/2 |
| Phase 3: Demo Users | Not Started | 0/2 |
| Phase 4: Export Data | Not Started | 0/3 |
| Phase 5: Import on Unraid | Not Started | 0/4 |

---

## Phase 1: Complete LLM Processing

### 1.1 Run LLM Analysis for PostHog
- [ ] **Task:** Process ~135 PRs missing LLM analysis
- **Command:**
  ```bash
  GROQ_API_KEY=<key> python manage.py run_llm_analysis --team "PostHog Analytics" --limit 200
  ```
- **Effort:** S (~5 min)
- **Acceptance Criteria:**
  - All PostHog PRs have `llm_summary` populated
  - No errors in console output

### 1.2 Run LLM Analysis for Polar
- [ ] **Task:** Process ~1,253 PRs missing LLM analysis
- **Command:**
  ```bash
  GROQ_API_KEY=<key> python manage.py run_llm_analysis --team "Polar.sh" --limit 1500
  ```
- **Effort:** M (~45 min)
- **Acceptance Criteria:**
  - All Polar PRs have `llm_summary` populated
  - No errors in console output

### 1.3 Verify LLM Coverage
- [ ] **Task:** Confirm 100% LLM coverage
- **Command:**
  ```sql
  SELECT t.name,
         COUNT(*) FILTER (WHERE llm_summary IS NOT NULL) * 100.0 / COUNT(*) as coverage_pct
  FROM metrics_pullrequest pr
  JOIN teams_team t ON t.id = pr.team_id
  WHERE t.slug IN ('posthog-demo', 'polar-demo')
  GROUP BY t.name;
  ```
- **Acceptance Criteria:**
  - Both teams show 100% coverage

---

## Phase 2: Generate Dashboard Insights

### 2.1 Generate Insights for PostHog
- [ ] **Task:** Create engineering insights for dashboard
- **Command:**
  ```bash
  python manage.py generate_insights --team-slug posthog-demo
  ```
- **Effort:** S (~1 min)
- **Acceptance Criteria:**
  - Insights visible in dashboard
  - At least 3 insights generated

### 2.2 Generate Insights for Polar
- [ ] **Task:** Create engineering insights for dashboard
- **Command:**
  ```bash
  python manage.py generate_insights --team-slug polar-demo
  ```
- **Effort:** S (~1 min)
- **Acceptance Criteria:**
  - Insights visible in dashboard
  - At least 3 insights generated

---

## Phase 3: Create Demo Users

### 3.1 Verify Teams Exist
- [ ] **Task:** Confirm demo teams are available
- **Command:**
  ```bash
  python manage.py setup_demo_users --list
  ```
- **Acceptance Criteria:**
  - `posthog-demo` team exists
  - `polar-demo` team exists

### 3.2 Create Demo User Accounts
- [ ] **Task:** Create demo users with passwords
- **Command:**
  ```bash
  python manage.py setup_demo_users
  ```
- **Effort:** S (~1 min)
- **Acceptance Criteria:**
  - `demo@posthog.com` created
  - `demo@polar.sh` created
  - Both users added to their respective teams

---

## Phase 4: Export Demo Data

### 4.1 Export Database Tables
- [ ] **Task:** Export relevant tables to SQL
- **Command:**
  ```bash
  pg_dump -h localhost -U tformance -d tformance \
    --data-only \
    --table=teams_team \
    --table=teams_membership \
    --table=users_customuser \
    --table=account_emailaddress \
    --table=metrics_* \
    -f demo_data.sql
  ```
- **Effort:** S (~5 min)
- **Acceptance Criteria:**
  - `demo_data.sql` file created
  - File contains data for demo teams

### 4.2 Compress Export (Optional)
- [ ] **Task:** Compress for faster transfer
- **Command:**
  ```bash
  gzip demo_data.sql
  # Creates demo_data.sql.gz
  ```
- **Acceptance Criteria:**
  - Compressed file created

### 4.3 Transfer to Unraid
- [ ] **Task:** Copy export file to Unraid server
- **Command:**
  ```bash
  scp demo_data.sql.gz unraid:/mnt/user/appdata/tformance/
  ```
- **Acceptance Criteria:**
  - File available on Unraid

---

## Phase 5: Import on Unraid

### 5.1 Backup Existing Data (Safety)
- [ ] **Task:** Create backup before import
- **Command:**
  ```bash
  docker exec tformance-db pg_dump -U tformance -d tformance > backup_before_demo.sql
  ```
- **Effort:** S
- **Acceptance Criteria:**
  - Backup file created

### 5.2 Clear Existing Demo Data (Optional)
- [ ] **Task:** Remove old demo data if exists
- **Command:**
  ```bash
  docker exec tformance-db psql -U tformance -d tformance -c "
    DELETE FROM metrics_pullrequest WHERE team_id IN (
      SELECT id FROM teams_team WHERE slug LIKE '%demo%'
    );
    DELETE FROM teams_membership WHERE team_id IN (
      SELECT id FROM teams_team WHERE slug LIKE '%demo%'
    );
    DELETE FROM teams_team WHERE slug LIKE '%demo%';
    DELETE FROM users_customuser WHERE email LIKE 'demo@%';
  "
  ```
- **Acceptance Criteria:**
  - Old demo data removed

### 5.3 Import Demo Data
- [ ] **Task:** Load exported data into Unraid
- **Command:**
  ```bash
  # Decompress if needed
  gunzip /mnt/user/appdata/tformance/demo_data.sql.gz

  # Import
  docker exec -i tformance-db psql -U tformance -d tformance < /mnt/user/appdata/tformance/demo_data.sql
  ```
- **Effort:** M (~10 min)
- **Acceptance Criteria:**
  - No import errors
  - Data visible in database

### 5.4 Verify Demo Environment
- [ ] **Task:** Test demo user login and data
- **Steps:**
  1. Navigate to https://dev2.ianchuk.com/accounts/login/
  2. Login as `demo@posthog.com` / `show_me_posthog_data`
  3. Verify dashboard shows data
  4. Logout and test `demo@polar.sh`
- **Acceptance Criteria:**
  - Both demo users can log in
  - Dashboard shows PR data
  - Insights visible
  - All pages load without errors

---

## Quick Reference

### All Commands in Order

```bash
# Phase 1: LLM Processing
GROQ_API_KEY=<key> python manage.py run_llm_analysis --team "PostHog Analytics" --limit 200
GROQ_API_KEY=<key> python manage.py run_llm_analysis --team "Polar.sh" --limit 1500

# Phase 2: Insights
python manage.py generate_insights --team-slug posthog-demo
python manage.py generate_insights --team-slug polar-demo

# Phase 3: Demo Users
python manage.py setup_demo_users

# Phase 4: Export
pg_dump -h localhost -U tformance -d tformance \
  --data-only \
  --table=teams_team \
  --table=teams_membership \
  --table=users_customuser \
  --table=account_emailaddress \
  --table=metrics_* \
  -f demo_data.sql

gzip demo_data.sql
scp demo_data.sql.gz unraid:/mnt/user/appdata/tformance/

# Phase 5: Import (on Unraid)
gunzip /mnt/user/appdata/tformance/demo_data.sql.gz
docker exec -i tformance-db psql -U tformance -d tformance < /mnt/user/appdata/tformance/demo_data.sql
```

### Demo Credentials

| Email | Password | Team |
|-------|----------|------|
| `demo@posthog.com` | `show_me_posthog_data` | PostHog Analytics |
| `demo@polar.sh` | `show_me_polar_data` | Polar.sh |

### URLs

- **Local:** http://localhost:8000/accounts/login/
- **Unraid:** https://dev2.ianchuk.com/accounts/login/
