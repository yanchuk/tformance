# File Categorization Expansion - Context

## Current State

### Existing Implementation
Located in `apps/metrics/models/github.py`:

```python
CATEGORY_CHOICES = [
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("test", "Test"),
    ("docs", "Documentation"),
    ("config", "Configuration"),
    ("javascript", "JavaScript (Ambiguous)"),
    ("other", "Other"),
]
```

### Supported Extensions (Current)
**Frontend**: .tsx, .jsx, .vue, .svelte, .css, .scss, .sass, .less, .html
**Backend**: .py, .go, .java, .rb, .rs, .kt, .kts, .scala, .php, .cs, .swift, .c, .cpp, .h, .hpp
**Test**: _test., test_, .spec., .test.
**Docs**: .md, .rst, .txt, .doc
**Config**: .json, .yaml, .yml, .toml, .ini, .env, .xml

### Path-Based Detection (Current)
For JavaScript/TypeScript files (.js, .ts, .mjs, .cjs):

**Backend Exception Patterns** (Tier 0):
- /pages/api/ (Next.js)
- /app/api/ (Next.js App Router)

**Frontend Path Patterns** (Tier 1):
- /components/, /hooks/, /contexts/, /composables/
- /store/, /stores/, /redux/, /pinia/, /vuex/
- /pages/, /views/, /layouts/, /screens/
- /frontend/, /client/, /web/, /ui/
- /apps/web/, /packages/ui/

**Backend Path Patterns** (Tier 2):
- /api/, /apis/, /endpoints/, /routes/, /routers/
- /controllers/, /services/, /handlers/, /resolvers/
- /middleware/, /middlewares/, /models/, /repositories/
- /backend/, /server/, /apps/api/, /packages/server/

## SO 2025 Survey Key Findings

### Programming Languages
| Rank | Language | Usage | YoY Change |
|------|----------|-------|------------|
| 1 | JavaScript | 66.0% | - |
| 2 | HTML/CSS | 61.9% | - |
| 3 | SQL | 58.6% | - |
| 4 | Python | 57.9% | **+7pp** |
| 5 | TypeScript | 43.6% | - |
| 6 | Java | 29.4% | - |
| 7 | C# | 27.8% | - |
| 8 | PHP | 18.9% | - |
| 9 | Go | 16.4% | - |
| 10 | Rust | 14.8% | Most admired (72%) |

**Notable additions needed**:
- Lua (9.2%) - Gaming, embedded
- Dart (5.9%) - Flutter/mobile frontend
- R (4.9%) - Data science
- Groovy (4.8%) - JVM scripting, Gradle
- Elixir (2.7%) - Phoenix framework
- Zig (2.1%) - Systems programming

### Web Frameworks
| Rank | Framework | Usage | Notes |
|------|-----------|-------|-------|
| 1 | Node.js | 48.7% | Runtime |
| 2 | React | 44.7% | Frontend |
| 3 | jQuery | 23.4% | Legacy |
| 4 | Next.js | 20.8% | Fullstack React |
| 5 | Express | 19.9% | Backend |
| 6 | FastAPI | ~15% | **+5pp** Python |
| 7 | Django | ~12% | Python |
| 8 | Vue.js | ~12% | Frontend |
| 9 | Angular | ~11% | Frontend |
| 10 | ASP.NET | ~14% | C# |

**Key trend**: FastAPI growth (+5pp) reflects Python's dominance in AI/ML

### AI Usage Insights
- **84%** using/planning AI tools (up from 76%)
- **51%** use AI daily (professionals)
- **46%** distrust AI accuracy
- **66%** frustrated by "almost right" code
- **52%** report productivity boost

**Top AI tools**:
1. ChatGPT (81.7%)
2. GitHub Copilot (67.9%)
3. Google Gemini (47.4%)
4. Claude Code (40.8%)
5. Microsoft Copilot (31.3%)

## Related Files

### Primary Implementation
- `apps/metrics/models/github.py` - PRFile model with categorize_file()

### Tests
- `apps/metrics/tests/models/test_pr_file.py` - Categorization tests

### Usage
- `apps/metrics/services/dashboard_service.py` - get_file_category_breakdown()
- `apps/metrics/seeding/real_project_seeder.py` - Uses categorization during seeding

## Dependencies

- No external dependencies needed
- Changes are internal to the categorization logic
- Backward compatible (adds new categories, doesn't break existing)

## Risks

1. **False positives**: New path patterns might incorrectly categorize files
   - Mitigation: Test against real repos before deployment

2. **Category inflation**: Too many specific categories reduce usefulness
   - Mitigation: Keep broad categories, use path detection for JS/TS only

3. **Survey changes**: Need migration for new AI tool options
   - Mitigation: Phase 3 is separate from file categorization
