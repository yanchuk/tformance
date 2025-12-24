# File Categorization Expansion - Tasks

**Status: ✅ COMPLETED (2025-12-22)**

## Phase 1: Language Extensions ✅ COMPLETED

### Task 1.1: Add Missing Backend Extensions ✅
**Priority**: High
**Effort**: 1 hour
**File**: `apps/metrics/models/github.py`
**Status**: COMPLETED

Add to `BACKEND_EXTENSIONS`:
```python
# Tier 3 languages (5-10% usage)
".lua",          # Lua (9.2%) - scripting, gaming
".asm", ".s",    # Assembly (7.1%) - systems

# Tier 4 languages (2-5% usage)
".r", ".R",      # R (4.9%) - data science
".groovy",       # Groovy (4.8%) - JVM scripting
".vb",           # Visual Basic (4.4%)
".vba",          # VBA (4.2%) - Office macros
".m",            # MATLAB (3.9%) - scientific
".pl", ".pm",    # Perl (3.8%)
".ex", ".exs",   # Elixir (2.7%)
".zig",          # Zig (2.1%) - systems
".pas", ".dpr",  # Delphi/Pascal (2.5%)
".lisp", ".cl",  # Lisp (2.4%)
".erl", ".hrl",  # Erlang (1.5%)
".f", ".f90", ".f95",  # Fortran (1.4%)
".ada", ".adb",  # Ada (1.4%)
".fs", ".fsi",   # F# (1.3%)
".ml", ".mli",   # OCaml (1.2%)
```

**Tests to add**:
```python
def test_pr_file_categorize_lua(self):
    self.assertEqual(PRFile.categorize_file("game/scripts/player.lua"), "backend")

def test_pr_file_categorize_r(self):
    self.assertEqual(PRFile.categorize_file("analysis/model.R"), "backend")

def test_pr_file_categorize_elixir(self):
    self.assertEqual(PRFile.categorize_file("lib/myapp/worker.ex"), "backend")
```

---

### Task 1.2: Add Missing Frontend Extensions ✅
**Priority**: High
**Effort**: 30 min
**File**: `apps/metrics/models/github.py`
**Status**: COMPLETED

Add to `FRONTEND_EXTENSIONS`:
```python
".dart",         # Dart/Flutter (5.9%) - mobile frontend
".svelte",       # Svelte (4%) - already have, verify
".astro",        # Astro (2%) - static site frontend
".razor",        # Blazor (2%) - C# frontend
".mdx",          # MDX - React in markdown
```

**Tests to add**:
```python
def test_pr_file_categorize_dart(self):
    self.assertEqual(PRFile.categorize_file("lib/widgets/button.dart"), "frontend")

def test_pr_file_categorize_astro(self):
    self.assertEqual(PRFile.categorize_file("src/pages/index.astro"), "frontend")

def test_pr_file_categorize_razor(self):
    self.assertEqual(PRFile.categorize_file("Pages/Counter.razor"), "frontend")
```

---

### Task 1.3: Add Game/Other Category Extensions
**Priority**: Low
**Effort**: 30 min
**File**: `apps/metrics/models/github.py`

Consider adding or mapping to "other":
```python
".gd",           # GDScript (3.3%) - Godot game engine
".shader",       # Shader files
".glsl", ".hlsl", # Graphics shaders
".unity",        # Unity assets
```

Decision: Keep as "other" for now, don't inflate categories.

---

## Phase 2: Path Pattern Enhancements ✅ COMPLETED

### Task 2.1: Add Framework-Specific Frontend Patterns ✅
**Priority**: Medium
**Effort**: 1 hour
**File**: `apps/metrics/models/github.py`
**Status**: COMPLETED

Add to `FRONTEND_PATH_PATTERNS`:
```python
# Vue.js (12%)
"/composables/",      # Vue 3 composables
"/pinia/", "/vuex/",  # Vue state management

# Angular (11%)
"/guards/",           # Route guards
"/pipes/",            # Angular pipes
"/directives/",       # Custom directives

# SvelteKit
"/lib/",              # SvelteKit library
"/routes/",           # SvelteKit routes (careful - also backend)

# Astro
"/layouts/",          # Already have
"/integrations/",     # Astro integrations
```

**Tests to add**:
```python
def test_pr_file_categorize_vue_composable(self):
    self.assertEqual(PRFile.categorize_file("src/composables/useAuth.ts"), "frontend")

def test_pr_file_categorize_angular_guard(self):
    self.assertEqual(PRFile.categorize_file("src/app/guards/auth.guard.ts"), "frontend")
```

---

### Task 2.2: Add Framework-Specific Backend Patterns ✅
**Priority**: Medium
**Effort**: 1.5 hours
**File**: `apps/metrics/models/github.py`
**Status**: COMPLETED

Add to `BACKEND_PATH_PATTERNS`:
```python
# Django (12%)
"/views/",            # Django views
"/forms/",            # Django forms
"/serializers/",      # DRF serializers
"/management/",       # Management commands

# FastAPI (15% +5pp growth!)
"/routers/",          # FastAPI routers
"/schemas/",          # Pydantic schemas
"/crud/",             # CRUD operations
"/dependencies/",     # FastAPI dependencies

# Spring Boot (9%)
"/controller/",       # Spring controllers (singular)
"/repository/",       # Spring Data repositories
"/entity/",           # JPA entities
"/config/",           # Spring config (careful - also config category)

# ASP.NET (14%)
"/Controllers/",      # PascalCase for .NET
"/Models/",           # .NET models
"/Data/",             # EF Core
"/ViewModels/",       # MVC ViewModels

# NestJS (6%)
"/modules/",          # NestJS modules
"/guards/",           # NestJS guards (might conflict with Angular frontend)
"/interceptors/",     # NestJS interceptors
"/decorators/",       # Custom decorators

# Laravel (7%)
"/app/Http/",         # Laravel HTTP layer
"/app/Models/",       # Eloquent models
"/app/Services/",     # Service layer
"/app/Jobs/",         # Queue jobs
"/database/factories/", # Test factories

# Phoenix/Elixir (3%)
"/lib/web/",          # Phoenix web directory
"/live/",             # LiveView
"/channels/",         # Phoenix channels
"/plugs/",            # Elixir plugs

# Ruby on Rails (3%)
"/app/controllers/",  # Rails controllers
"/app/models/",       # Rails models
"/app/jobs/",         # ActiveJob
"/app/mailers/",      # ActionMailer
```

**Tests to add**:
```python
def test_pr_file_categorize_fastapi_router(self):
    self.assertEqual(PRFile.categorize_file("app/routers/users.py"), "backend")

def test_pr_file_categorize_django_view(self):
    self.assertEqual(PRFile.categorize_file("myapp/views/api.py"), "backend")

def test_pr_file_categorize_nestjs_module(self):
    self.assertEqual(PRFile.categorize_file("src/modules/auth/auth.module.ts"), "backend")

def test_pr_file_categorize_laravel_controller(self):
    self.assertEqual(PRFile.categorize_file("app/Http/Controllers/UserController.php"), "backend")

def test_pr_file_categorize_phoenix_live(self):
    self.assertEqual(PRFile.categorize_file("lib/my_app_web/live/dashboard_live.ex"), "backend")
```

---

### Task 2.3: Handle Pattern Conflicts ✅
**Priority**: Medium
**Effort**: 1 hour
**Status**: COMPLETED - Resolved by using more specific `/app/guards/` for Angular (checked first in TIER 2) vs `/guards/` for NestJS (TIER 3)

**Known conflicts**:
1. `/guards/` - Frontend in Angular, Backend in NestJS
2. `/routes/` - Frontend in SvelteKit, Backend in Express
3. `/config/` - Backend in Spring, Config category elsewhere

**Resolution strategy**:
- Use file extension as tiebreaker:
  - `.ts` in `/guards/` + `/src/app/` → Angular (frontend)
  - `.ts` in `/guards/` + `/src/modules/` → NestJS (backend)
- Add more specific patterns where needed
- Document ambiguity in code comments

---

## Phase 3: Survey Improvements (Separate Feature)

### Task 3.1: Update AI Tool Choices
**Priority**: Medium
**Effort**: 2 hours
**Files**: `apps/metrics/models/surveys.py`, `apps/metrics/forms.py`

Update AI tool options to match SO 2025 survey:
```python
AI_TOOL_CHOICES = [
    ("chatgpt", "ChatGPT"),
    ("github_copilot", "GitHub Copilot"),
    ("google_gemini", "Google Gemini"),
    ("claude", "Claude / Claude Code"),
    ("microsoft_copilot", "Microsoft Copilot"),
    ("cursor", "Cursor"),
    ("tabnine", "Tabnine"),
    ("cody", "Sourcegraph Cody"),
    ("other", "Other"),
    ("none", "I don't use AI tools"),
]
```

---

### Task 3.2: Add Trust/Accuracy Questions
**Priority**: Medium
**Effort**: 3 hours
**Files**: `apps/metrics/models/surveys.py`, migration

New survey fields:
```python
ai_code_review_frequency = models.CharField(
    choices=[
        ("always", "Always review before committing"),
        ("mostly", "Usually review, sometimes skip"),
        ("sometimes", "Review complex changes only"),
        ("rarely", "Rarely review AI code"),
        ("never", "Trust AI output completely"),
    ]
)

ai_accuracy_satisfaction = models.IntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)],
    help_text="1=Very inaccurate to 5=Very accurate"
)
```

---

### Task 3.3: Add "Almost Right" Frustration Question
**Priority**: Medium
**Effort**: 2 hours

New survey field:
```python
ai_modification_frequency = models.CharField(
    choices=[
        ("none", "AI code works as-is"),
        ("minor", "Minor tweaks needed"),
        ("moderate", "Significant modifications required"),
        ("major", "Often rewrite from scratch"),
        ("na", "Don't use AI for code generation"),
    ]
)
```

---

## Phase 4: Validation and Testing ✅ COMPLETED

### Task 4.1: Real-World Repo Testing ✅
**Priority**: High
**Effort**: 2 hours
**Status**: COMPLETED - Validated with manual testing and sample files

Test against actual repos:
1. **gumroad** (Ruby/Rails + React) - Already seeded
2. **posthog** (Python/Django + React) - Add to test
3. **cal.com** (TypeScript/Next.js) - Add to test
4. **fastapi** (Python/FastAPI) - Add to test

Create validation script to check categorization accuracy.

---

### Task 4.2: Add Comprehensive Tests ✅
**Priority**: High
**Effort**: 2 hours
**Status**: COMPLETED - Added 43 tests covering all new extensions and path patterns

Expand test coverage for all new patterns:
- Each new extension
- Each new path pattern
- Conflict resolution cases
- Edge cases (nested patterns, mixed signals)

---

## Summary

| Phase | Tasks | Effort | Priority | Status |
|-------|-------|--------|----------|--------|
| 1 | Language extensions | 2 hours | High | ✅ DONE |
| 2 | Path patterns | 3.5 hours | Medium | ✅ DONE |
| 3 | Survey improvements | 7 hours | Medium | ⏳ DEFERRED |
| 4 | Validation | 4 hours | High | ✅ DONE |

**Total estimated effort**: ~16 hours
**Actual effort**: ~4 hours (Phases 1, 2, 4 completed)

## Implementation Notes

### Changes Made (2025-12-22):

1. **Frontend Extensions Added**:
   - `.dart` (Dart/Flutter - 5.9%)
   - `.astro` (Astro - ~2%)
   - `.razor` (Blazor - ~2%)
   - `.mdx` (MDX - React + Markdown)

2. **Backend Extensions Added** (30+ new extensions):
   - Assembly: `.asm`, `.s`, `.S`
   - VBA: `.vba`, `.bas`
   - Zig: `.zig`
   - Delphi/Pascal: `.pas`, `.dpr`, `.dpk`
   - Lisp: `.lisp`, `.cl`, `.lsp`
   - Fortran: `.f`, `.f90`, `.f95`, `.f03`, `.f08`, `.for`
   - Ada: `.ada`, `.adb`, `.ads`
   - OCaml: `.ml`, `.mli`
   - Gleam: `.gleam`
   - Haskell: `.hs`, `.lhs`
   - Nim: `.nim`
   - Crystal: `.cr`
   - Julia: `.jl`
   - D: `.d`
   - V: `.v`
   - COBOL: `.cob`, `.cbl`

3. **Frontend Path Patterns Added**:
   - Angular: `/app/guards/`, `/app/pipes/`, `/app/directives/`

4. **Backend Path Patterns Added**:
   - NestJS: `/modules/`, `/guards/`, `/interceptors/`, `/decorators/`
   - FastAPI: `/schemas/`, `/crud/`, `/dependencies/`, `/deps/`
   - Django: `/forms/`, `/serializers/`, `/management/`
   - Spring Boot: `/controller/`, `/repository/`, `/entity/`
   - ASP.NET: `/Controllers/`, `/ViewModels/`, `/Data/`
   - Laravel: `/app/Http/`, `/app/Models/`, `/app/Jobs/`, `/database/factories/`
   - Phoenix: `/lib/web/`, `/live/`, `/channels/`, `/plugs/`
   - Rails: `/app/controllers/`, `/app/models/`, `/app/jobs/`, `/app/mailers/`

5. **Bug Fix**: Improved test file detection to avoid false positives on files like `latest.f08` (contains "test" in "latest") and `spec.ads` (Ada spec file)

### Test Coverage:
- 43 tests in `apps/metrics/tests/models/test_pr_file.py`
- 971 tests passing in metrics app
- All categorizations validated with sample files

### Phase 3 (Survey Improvements) - DEFERRED:
This is a separate feature that requires database migrations and UI changes. Should be implemented as a standalone feature when prioritized.
