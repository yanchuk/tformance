# File Categorization Expansion Plan

**Last Updated: 2025-12-22**

## Executive Summary

Extend `PRFile.categorize_file()` to support all popular programming languages and frameworks based on Stack Overflow 2025 Developer Survey data. Also improve AI usage surveys based on SO 2025 AI section insights.

**Key insight**: Current implementation already covers most Tier 1-2 languages. Focus is on:
1. Adding missing frontend extensions (Dart, Astro, Razor)
2. Adding missing backend extensions (Assembly, Zig, Delphi, Lisp, VBA)
3. Adding framework-specific path patterns (FastAPI, Laravel, Phoenix, NestJS)
4. Survey improvements based on AI trust/accuracy findings

## Data Source: Stack Overflow 2025 Developer Survey

Survey responses from ~49,000 developers worldwide.

---

## Part 1: Programming Languages Gap Analysis

### Already Supported (No Action Needed)

| Language | Usage | Status |
|----------|-------|--------|
| JavaScript | 66.0% | ✅ Path detection |
| HTML/CSS | 61.9% | ✅ .html, .css, etc. |
| Python | 57.9% | ✅ .py, .pyw, .pyx |
| TypeScript | 43.6% | ✅ Path detection |
| Java | 29.4% | ✅ .java |
| C# | 27.8% | ✅ .cs |
| C++ | 23.5% | ✅ .cpp, .hpp, etc. |
| C | 22.0% | ✅ .c, .h |
| PHP | 18.9% | ✅ .php, .phtml, etc. |
| Go | 16.4% | ✅ .go |
| Rust | 14.8% | ✅ .rs |
| Kotlin | 10.8% | ✅ .kt, .kts |
| Lua | 9.2% | ✅ .lua |
| Ruby | 6.4% | ✅ .rb, .erb |
| Swift | 5.4% | ✅ .swift |
| R | 4.9% | ✅ .r, .R |
| Groovy | 4.8% | ✅ .groovy |
| VB.NET | 4.4% | ✅ .vb |
| Perl | 3.8% | ✅ .pl, .pm |
| Elixir | 2.7% | ✅ .ex, .exs |
| Scala | 2.6% | ✅ .scala |
| F# | 1.3% | ✅ .fs |
| Erlang | 1.5% | ✅ .erl, .hrl |
| Clojure | - | ✅ .clj, .cljs |

### Missing - Need to Add

| Language | Usage | Extension | Category | Priority |
|----------|-------|-----------|----------|----------|
| **Dart** | **5.9%** | .dart | frontend | **HIGH** |
| Assembly | 7.1% | .asm, .s | backend | Medium |
| VBA | 4.2% | .vba | backend | Low |
| MATLAB | 3.9% | .mat | backend | Low |
| GDScript | 3.3% | .gd | other | Low |
| Zig | 2.1% | .zig | backend | Low |
| Delphi | 2.5% | .pas, .dpr | backend | Low |
| Lisp | 2.4% | .lisp, .cl | backend | Low |
| Fortran | 1.4% | .f, .f90, .f95 | backend | Low |
| Ada | 1.4% | .ada, .adb | backend | Low |
| OCaml | 1.2% | .ml, .mli | backend | Low |
| Gleam | 1.1% | .gleam | backend | Low |
| **Astro** | **~2%** | .astro | frontend | **HIGH** |
| **Blazor** | **~2%** | .razor | frontend | **HIGH** |

---

## Part 2: Web Frameworks Gap Analysis

### Path Patterns Already Implemented

| Framework | Pattern | Status |
|-----------|---------|--------|
| React | /components/, /hooks/, /contexts/ | ✅ |
| Vue.js | /composables/, /pinia/, /vuex/ | ✅ |
| Next.js | /pages/api/, /app/api/ (exceptions) | ✅ |
| Express | /routes/, /controllers/, /middleware/ | ✅ |
| General | /services/, /handlers/, /resolvers/ | ✅ |
| Monorepo | /apps/web/, /packages/ui/, etc. | ✅ |

### Path Patterns Missing

| Framework | Usage | Patterns Needed | Priority |
|-----------|-------|-----------------|----------|
| **FastAPI** | **~15% (+5pp)** | /schemas/, /crud/, /dependencies/ | **HIGH** |
| Django | ~12% | /forms/, /serializers/, /management/ | Medium |
| Laravel | ~7% | /app/Http/, /app/Models/, /app/Jobs/ | Medium |
| NestJS | ~6% | /modules/, /guards/, /interceptors/, /decorators/ | Medium |
| Spring Boot | ~9% | /entity/, /repository/ (singular) | Medium |
| Phoenix | ~3% | /lib/web/, /live/, /channels/, /plugs/ | Low |
| ASP.NET | ~14% | /Controllers/, /ViewModels/, /Data/ | Medium |
| Rails | ~3% | /app/jobs/, /app/mailers/ | Low |

---

## Part 3: AI Survey Insights (SO 2025 AI Section)

### Key Statistics

| Metric | Value | Implication |
|--------|-------|-------------|
| AI tool usage | 84% (up from 76%) | Growing adoption |
| Daily AI users (pros) | 51% | Half use daily |
| Trust AI accuracy | 33% | **Minority trust** |
| Distrust AI accuracy | 46% | **Majority distrust** |
| Top frustration | "Almost right but not quite" (66%) | Quality issue |
| Productivity boost reported | 52% | Perceived benefit |
| Sentiment (favorable) | 60% (down from 70%+) | Cooling enthusiasm |

### AI Tool Market Share (for survey options)

| Tool | Usage |
|------|-------|
| ChatGPT | 81.7% |
| GitHub Copilot | 67.9% |
| Google Gemini | 47.4% |
| Claude / Claude Code | 40.8% |
| Microsoft Copilot | 31.3% |
| Perplexity | 16.2% |
| Tabnine | 5.0% |
| Cursor | - |

### Survey Improvement Recommendations

1. **Expand AI tool choices** - Add Cursor, Perplexity, Claude Code
2. **Add trust/accuracy questions** - Key finding from SO 2025
3. **Add "almost right" frustration question** - 66% top complaint
4. **Separate simple vs complex task questions** - Different satisfaction levels
5. **Track AI agent usage** - Emerging (14% daily, 31% total)

---

## Implementation Phases

### Phase 1: Extension Additions (TDD)
**Effort**: Small (2 hours)
**Risk**: Low
**Files**: `apps/metrics/models/github.py`, `apps/metrics/tests/models/test_pr_file.py`

Add missing extensions:
```python
# Frontend (add to FRONTEND_EXTENSIONS)
".dart",     # Dart/Flutter (5.9%)
".astro",    # Astro (2%)
".razor",    # Blazor (2%)
".mdx",      # MDX (React + Markdown)

# Backend (add to BACKEND_EXTENSIONS)
".asm", ".s",        # Assembly (7.1%)
".vba",              # VBA (4.2%)
".mat",              # MATLAB (3.9%)
".zig",              # Zig (2.1%)
".pas", ".dpr",      # Delphi (2.5%)
".lisp", ".cl",      # Lisp (2.4%)
".f", ".f90", ".f95", # Fortran (1.4%)
".ada", ".adb",      # Ada (1.4%)
".ml", ".mli",       # OCaml (1.2%)
".gleam",            # Gleam (1.1%)
".gd",               # GDScript (3.3%) - or "other"
```

### Phase 2: Path Pattern Additions (TDD)
**Effort**: Medium (4 hours)
**Risk**: Medium (potential conflicts)
**Files**: `apps/metrics/models/github.py`, `apps/metrics/tests/models/test_pr_file.py`

Add framework-specific patterns:
```python
# Backend patterns (add to BACKEND_PATH_PATTERNS)
"/schemas/",         # FastAPI Pydantic schemas
"/crud/",            # FastAPI CRUD operations
"/dependencies/",    # FastAPI dependencies
"/forms/",           # Django forms
"/serializers/",     # DRF serializers
"/management/",      # Django management commands
"/app/Http/",        # Laravel HTTP layer
"/app/Models/",      # Laravel Eloquent
"/app/Jobs/",        # Laravel/Rails jobs
"/app/Mailers/",     # Rails ActionMailer
"/modules/",         # NestJS modules
"/interceptors/",    # NestJS interceptors
"/decorators/",      # NestJS custom decorators
"/entity/",          # Spring Boot JPA entities
"/repository/",      # Spring Data (singular)
"/lib/web/",         # Phoenix web
"/live/",            # Phoenix LiveView
"/channels/",        # Phoenix channels
"/plugs/",           # Phoenix plugs
"/Controllers/",     # ASP.NET (PascalCase)
"/ViewModels/",      # ASP.NET MVC
"/Data/",            # EF Core
```

### Phase 3: Survey Improvements (Separate Feature)
**Effort**: Large (8-12 hours)
**Risk**: Medium (migration, UI changes)
**Files**: `apps/metrics/models/surveys.py`, migrations, templates

1. Update AI tool choices in `PRSurvey.ai_tools_used`
2. Add new survey fields:
   - `ai_code_review_frequency`
   - `ai_accuracy_satisfaction`
   - `ai_modification_frequency`
3. Create migration
4. Update survey templates and forms
5. Update dashboard metrics

### Phase 4: Validation & Testing
**Effort**: Medium (4 hours)
**Risk**: Low

1. Run categorization on seeded repos (gumroad, etc.)
2. Sample 100 random PRs for manual accuracy check
3. Track "javascript" (ambiguous) rate as quality metric
4. Performance test with large PRs

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Extension coverage | 95%+ of SO 2025 top 30 | Checklist verification |
| Path detection accuracy | >90% | Manual review of 100 PRs |
| "javascript" (ambiguous) rate | <15% | Dashboard metric |
| Test coverage | 100% of new patterns | pytest coverage |

---

## References

- Stack Overflow 2025 Developer Survey: https://survey.stackoverflow.co/2025/
- Technology section: https://survey.stackoverflow.co/2025/technology/
- AI section: https://survey.stackoverflow.co/2025/ai/
- Current implementation: `apps/metrics/models/github.py:454-766`
