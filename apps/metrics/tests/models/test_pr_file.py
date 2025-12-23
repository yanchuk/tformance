from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    PRFile,
    PullRequest,
    TeamMember,
)
from apps.teams.context import unset_current_team
from apps.teams.models import Team


class TestPRFileModel(TestCase):
    """Tests for PRFile model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(
            team=self.team,
            display_name="John Doe",
            github_username="johndoe",
            github_id="123",
        )
        self.pull_request = PullRequest.objects.create(
            team=self.team,
            github_pr_id=1,
            github_repo="org/repo",
            title="Test PR",
            author=self.author,
            state="open",
            pr_created_at=django_timezone.now(),
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_file_creation(self):
        """Test that PRFile can be created with all required fields."""
        pr_file = PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="src/components/Button.tsx",
            status="modified",
            additions=10,
            deletions=5,
            changes=15,
            file_category="frontend",
        )
        self.assertEqual(pr_file.filename, "src/components/Button.tsx")
        self.assertEqual(pr_file.status, "modified")
        self.assertEqual(pr_file.additions, 10)
        self.assertEqual(pr_file.deletions, 5)
        self.assertEqual(pr_file.changes, 15)
        self.assertEqual(pr_file.file_category, "frontend")
        self.assertIsNotNone(pr_file.pk)

    def test_pr_file_pull_request_relationship(self):
        """Test that PRFile has correct foreign key relationship with PullRequest."""
        file1 = PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="src/app.py",
            status="modified",
            additions=20,
            deletions=10,
            changes=30,
            file_category="backend",
        )
        file2 = PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="README.md",
            status="modified",
            additions=5,
            deletions=2,
            changes=7,
            file_category="docs",
        )

        # Test forward relationship
        self.assertEqual(file1.pull_request, self.pull_request)
        self.assertEqual(file2.pull_request, self.pull_request)

        # Test reverse relationship via related_name='files'
        files = self.pull_request.files.all()
        self.assertEqual(files.count(), 2)
        self.assertIn(file1, files)
        self.assertIn(file2, files)

    def test_pr_file_unique_constraint(self):
        """Test that unique constraint on (team, pull_request, filename) is enforced."""
        PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="src/utils.py",
            status="added",
            additions=100,
            deletions=0,
            changes=100,
            file_category="backend",
        )
        # Attempt to create another file with same team, pull_request, and filename
        with self.assertRaises(IntegrityError):
            PRFile.objects.create(
                team=self.team,
                pull_request=self.pull_request,
                filename="src/utils.py",
                status="modified",
                additions=10,
                deletions=5,
                changes=15,
                file_category="backend",
            )

    def test_pr_file_categorize_frontend(self):
        """Test that frontend files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("src/App.tsx"), "frontend")
        self.assertEqual(PRFile.categorize_file("components/Button.jsx"), "frontend")
        self.assertEqual(PRFile.categorize_file("pages/Home.vue"), "frontend")
        self.assertEqual(PRFile.categorize_file("styles/main.css"), "frontend")
        self.assertEqual(PRFile.categorize_file("styles/app.scss"), "frontend")
        self.assertEqual(PRFile.categorize_file("templates/index.html"), "frontend")

    def test_pr_file_categorize_backend(self):
        """Test that backend files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("src/app.py"), "backend")
        self.assertEqual(PRFile.categorize_file("main.go"), "backend")
        self.assertEqual(PRFile.categorize_file("src/Main.java"), "backend")
        self.assertEqual(PRFile.categorize_file("app/controllers/user.rb"), "backend")
        self.assertEqual(PRFile.categorize_file("src/lib.rs"), "backend")

    def test_pr_file_categorize_test(self):
        """Test that test files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("src/app_test.py"), "test")
        self.assertEqual(PRFile.categorize_file("test_utils.py"), "test")
        self.assertEqual(PRFile.categorize_file("tests/integration_test.go"), "test")
        self.assertEqual(PRFile.categorize_file("components/Button.spec.tsx"), "test")
        self.assertEqual(PRFile.categorize_file("app.spec.js"), "test")

    def test_pr_file_categorize_docs(self):
        """Test that documentation files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("README.md"), "docs")
        self.assertEqual(PRFile.categorize_file("docs/setup.rst"), "docs")
        self.assertEqual(PRFile.categorize_file("CHANGELOG.txt"), "docs")

    def test_pr_file_categorize_config(self):
        """Test that configuration files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("package.json"), "config")
        self.assertEqual(PRFile.categorize_file("config.yaml"), "config")
        self.assertEqual(PRFile.categorize_file("settings.yml"), "config")
        self.assertEqual(PRFile.categorize_file("pyproject.toml"), "config")
        self.assertEqual(PRFile.categorize_file("setup.ini"), "config")
        self.assertEqual(PRFile.categorize_file(".env"), "config")

    def test_pr_file_categorize_javascript_frontend_paths(self):
        """Test that JS/TS files in frontend directories are categorized as frontend."""
        # Component directories
        self.assertEqual(PRFile.categorize_file("src/components/Button.js"), "frontend")
        self.assertEqual(PRFile.categorize_file("components/Modal.ts"), "frontend")

        # React-specific directories
        self.assertEqual(PRFile.categorize_file("src/hooks/useAuth.ts"), "frontend")
        self.assertEqual(PRFile.categorize_file("src/contexts/ThemeContext.js"), "frontend")
        self.assertEqual(PRFile.categorize_file("src/store/userSlice.ts"), "frontend")
        self.assertEqual(PRFile.categorize_file("src/redux/actions.js"), "frontend")

        # Page directories
        self.assertEqual(PRFile.categorize_file("src/pages/Home.ts"), "frontend")
        self.assertEqual(PRFile.categorize_file("pages/index.js"), "frontend")
        self.assertEqual(PRFile.categorize_file("views/Dashboard.ts"), "frontend")

        # Explicit frontend directories
        self.assertEqual(PRFile.categorize_file("frontend/app.js"), "frontend")
        self.assertEqual(PRFile.categorize_file("client/store.ts"), "frontend")
        self.assertEqual(PRFile.categorize_file("web/main.js"), "frontend")

        # Monorepo patterns
        self.assertEqual(PRFile.categorize_file("apps/web/src/index.ts"), "frontend")
        self.assertEqual(PRFile.categorize_file("packages/ui/Button.js"), "frontend")

    def test_pr_file_categorize_javascript_backend_paths(self):
        """Test that JS/TS files in backend directories are categorized as backend."""
        # API directories
        self.assertEqual(PRFile.categorize_file("src/api/users.ts"), "backend")
        self.assertEqual(PRFile.categorize_file("api/routes.js"), "backend")

        # Service layer
        self.assertEqual(PRFile.categorize_file("src/controllers/auth.ts"), "backend")
        self.assertEqual(PRFile.categorize_file("src/services/userService.js"), "backend")
        self.assertEqual(PRFile.categorize_file("handlers/webhook.ts"), "backend")

        # Data layer
        self.assertEqual(PRFile.categorize_file("models/User.js"), "backend")
        self.assertEqual(PRFile.categorize_file("src/repositories/userRepo.ts"), "backend")
        self.assertEqual(PRFile.categorize_file("prisma/seed.ts"), "backend")

        # Explicit backend directories
        self.assertEqual(PRFile.categorize_file("server/index.js"), "backend")
        self.assertEqual(PRFile.categorize_file("backend/routes.ts"), "backend")

        # Monorepo patterns
        self.assertEqual(PRFile.categorize_file("apps/api/src/index.ts"), "backend")
        self.assertEqual(PRFile.categorize_file("packages/server/main.js"), "backend")

    def test_pr_file_categorize_javascript_nextjs_api_routes(self):
        """Test that Next.js API routes are correctly categorized as backend."""
        # TIER 1: Backend exceptions - these should be backend even though /pages/ is frontend
        self.assertEqual(PRFile.categorize_file("pages/api/users.ts"), "backend")
        self.assertEqual(PRFile.categorize_file("pages/api/auth/login.js"), "backend")
        self.assertEqual(PRFile.categorize_file("src/pages/api/webhook.ts"), "backend")

        # Next.js App Router API routes
        self.assertEqual(PRFile.categorize_file("app/api/users/route.ts"), "backend")
        self.assertEqual(PRFile.categorize_file("src/app/api/auth/route.js"), "backend")

        # Regular pages should still be frontend
        self.assertEqual(PRFile.categorize_file("pages/index.ts"), "frontend")
        self.assertEqual(PRFile.categorize_file("pages/about.js"), "frontend")

    def test_pr_file_categorize_javascript_ambiguous(self):
        """Test that JS/TS files without matching patterns fall back to 'javascript'."""
        # Root level files - no path context
        self.assertEqual(PRFile.categorize_file("index.js"), "javascript")
        self.assertEqual(PRFile.categorize_file("main.ts"), "javascript")

        # Unknown directory patterns
        self.assertEqual(PRFile.categorize_file("foo/bar.mjs"), "javascript")
        self.assertEqual(PRFile.categorize_file("src/unknown/file.ts"), "javascript")

    def test_pr_file_categorize_jsx_tsx_always_frontend(self):
        """Test that JSX/TSX files are always frontend (React components)."""
        self.assertEqual(PRFile.categorize_file("src/App.tsx"), "frontend")
        self.assertEqual(PRFile.categorize_file("components/Button.jsx"), "frontend")
        # Even in API directory, JSX/TSX is frontend (React component)
        self.assertEqual(PRFile.categorize_file("api/components/Form.tsx"), "frontend")

    def test_pr_file_categorize_other(self):
        """Test that unrecognized files are categorized as 'other'."""
        self.assertEqual(PRFile.categorize_file("data.csv"), "other")
        self.assertEqual(PRFile.categorize_file("image.png"), "other")
        self.assertEqual(PRFile.categorize_file("unknown.xyz"), "other")

    # ==========================================================================
    # Phase 1: Additional Language Extensions (SO 2025 Survey Coverage)
    # ==========================================================================

    def test_pr_file_categorize_dart_flutter(self):
        """Test that Dart/Flutter files are categorized as frontend (5.9% usage)."""
        self.assertEqual(PRFile.categorize_file("lib/widgets/button.dart"), "frontend")
        self.assertEqual(PRFile.categorize_file("lib/main.dart"), "frontend")
        self.assertEqual(PRFile.categorize_file("lib/screens/home_screen.dart"), "frontend")

    def test_pr_file_categorize_astro(self):
        """Test that Astro files are categorized as frontend (~2% usage)."""
        self.assertEqual(PRFile.categorize_file("src/pages/index.astro"), "frontend")
        self.assertEqual(PRFile.categorize_file("src/components/Header.astro"), "frontend")
        self.assertEqual(PRFile.categorize_file("src/layouts/Layout.astro"), "frontend")

    def test_pr_file_categorize_blazor_razor(self):
        """Test that Blazor/Razor files are categorized as frontend (~2% usage)."""
        self.assertEqual(PRFile.categorize_file("Pages/Counter.razor"), "frontend")
        self.assertEqual(PRFile.categorize_file("Shared/NavMenu.razor"), "frontend")
        self.assertEqual(PRFile.categorize_file("Components/Modal.razor"), "frontend")

    def test_pr_file_categorize_mdx(self):
        """Test that MDX files (React + Markdown) are categorized as frontend."""
        self.assertEqual(PRFile.categorize_file("docs/intro.mdx"), "frontend")
        self.assertEqual(PRFile.categorize_file("content/blog/post.mdx"), "frontend")

    def test_pr_file_categorize_assembly(self):
        """Test that Assembly files are categorized as backend (7.1% usage)."""
        self.assertEqual(PRFile.categorize_file("src/boot.asm"), "backend")
        self.assertEqual(PRFile.categorize_file("kernel/entry.s"), "backend")
        self.assertEqual(PRFile.categorize_file("arch/x86/start.S"), "backend")

    def test_pr_file_categorize_vba(self):
        """Test that VBA files are categorized as backend (4.2% usage)."""
        self.assertEqual(PRFile.categorize_file("macros/export.vba"), "backend")
        self.assertEqual(PRFile.categorize_file("modules/utils.bas"), "backend")

    def test_pr_file_categorize_matlab(self):
        """Test that MATLAB files are categorized as backend (3.9% usage)."""
        self.assertEqual(PRFile.categorize_file("analysis/model.m"), "backend")
        self.assertEqual(PRFile.categorize_file("scripts/plot_data.m"), "backend")

    def test_pr_file_categorize_zig(self):
        """Test that Zig files are categorized as backend (2.1% usage)."""
        self.assertEqual(PRFile.categorize_file("src/main.zig"), "backend")
        self.assertEqual(PRFile.categorize_file("lib/allocator.zig"), "backend")

    def test_pr_file_categorize_delphi_pascal(self):
        """Test that Delphi/Pascal files are categorized as backend (2.5% usage)."""
        self.assertEqual(PRFile.categorize_file("src/MainForm.pas"), "backend")
        self.assertEqual(PRFile.categorize_file("src/Project1.dpr"), "backend")
        self.assertEqual(PRFile.categorize_file("units/Utils.pas"), "backend")

    def test_pr_file_categorize_lisp(self):
        """Test that Lisp files are categorized as backend (2.4% usage)."""
        self.assertEqual(PRFile.categorize_file("src/core.lisp"), "backend")
        self.assertEqual(PRFile.categorize_file("src/utils.cl"), "backend")
        self.assertEqual(PRFile.categorize_file("lib/package.lisp"), "backend")

    def test_pr_file_categorize_fortran(self):
        """Test that Fortran files are categorized as backend (1.4% usage)."""
        self.assertEqual(PRFile.categorize_file("src/solver.f"), "backend")
        self.assertEqual(PRFile.categorize_file("src/matrix.f90"), "backend")
        self.assertEqual(PRFile.categorize_file("lib/utils.f95"), "backend")
        self.assertEqual(PRFile.categorize_file("src/modern.f03"), "backend")
        self.assertEqual(PRFile.categorize_file("src/latest.f08"), "backend")

    def test_pr_file_categorize_ada(self):
        """Test that Ada files are categorized as backend (1.4% usage)."""
        self.assertEqual(PRFile.categorize_file("src/main.ada"), "backend")
        self.assertEqual(PRFile.categorize_file("src/package.adb"), "backend")
        self.assertEqual(PRFile.categorize_file("src/spec.ads"), "backend")

    def test_pr_file_categorize_ocaml(self):
        """Test that OCaml files are categorized as backend (1.2% usage)."""
        self.assertEqual(PRFile.categorize_file("src/main.ml"), "backend")
        self.assertEqual(PRFile.categorize_file("lib/types.mli"), "backend")
        self.assertEqual(PRFile.categorize_file("src/parser.ml"), "backend")

    def test_pr_file_categorize_gleam(self):
        """Test that Gleam files are categorized as backend (1.1% usage)."""
        self.assertEqual(PRFile.categorize_file("src/app.gleam"), "backend")
        self.assertEqual(PRFile.categorize_file("src/web/router.gleam"), "backend")

    def test_pr_file_categorize_gdscript(self):
        """Test that GDScript files (Godot) are categorized as other (3.3% usage)."""
        # GDScript is for game development, categorize as "other" to not inflate backend
        self.assertEqual(PRFile.categorize_file("scripts/player.gd"), "other")
        self.assertEqual(PRFile.categorize_file("scenes/enemy.gd"), "other")

    def test_pr_file_categorize_haskell(self):
        """Test that Haskell files are categorized as backend."""
        self.assertEqual(PRFile.categorize_file("src/Main.hs"), "backend")
        self.assertEqual(PRFile.categorize_file("lib/Types.lhs"), "backend")

    def test_pr_file_categorize_nim(self):
        """Test that Nim files are categorized as backend."""
        self.assertEqual(PRFile.categorize_file("src/main.nim"), "backend")
        self.assertEqual(PRFile.categorize_file("src/utils.nim"), "backend")

    def test_pr_file_categorize_crystal(self):
        """Test that Crystal files are categorized as backend."""
        self.assertEqual(PRFile.categorize_file("src/app.cr"), "backend")
        self.assertEqual(PRFile.categorize_file("src/models/user.cr"), "backend")

    def test_pr_file_categorize_julia(self):
        """Test that Julia files are categorized as backend."""
        self.assertEqual(PRFile.categorize_file("src/analysis.jl"), "backend")
        self.assertEqual(PRFile.categorize_file("lib/solver.jl"), "backend")

    # ==========================================================================
    # Phase 2: Framework-Specific Path Patterns (SO 2025 Survey Coverage)
    # ==========================================================================

    def test_pr_file_categorize_fastapi_paths(self):
        """Test that FastAPI-specific paths are categorized as backend (~15% usage, +5pp growth)."""
        # FastAPI schemas (Pydantic models)
        self.assertEqual(PRFile.categorize_file("app/schemas/user.py"), "backend")
        self.assertEqual(PRFile.categorize_file("src/schemas/order.py"), "backend")
        # FastAPI CRUD operations
        self.assertEqual(PRFile.categorize_file("app/crud/user.py"), "backend")
        self.assertEqual(PRFile.categorize_file("src/crud/items.py"), "backend")
        # FastAPI dependencies
        self.assertEqual(PRFile.categorize_file("app/dependencies/auth.py"), "backend")
        self.assertEqual(PRFile.categorize_file("src/deps/database.py"), "backend")

    def test_pr_file_categorize_django_paths(self):
        """Test that Django-specific paths are categorized as backend (~12% usage)."""
        # Django views
        self.assertEqual(PRFile.categorize_file("myapp/views/api.py"), "backend")
        self.assertEqual(PRFile.categorize_file("apps/users/views.py"), "backend")
        # Django forms
        self.assertEqual(PRFile.categorize_file("myapp/forms/registration.py"), "backend")
        self.assertEqual(PRFile.categorize_file("apps/orders/forms.py"), "backend")
        # DRF serializers
        self.assertEqual(PRFile.categorize_file("api/serializers/user.py"), "backend")
        self.assertEqual(PRFile.categorize_file("apps/products/serializers.py"), "backend")
        # Django management commands
        self.assertEqual(PRFile.categorize_file("myapp/management/commands/sync.py"), "backend")

    def test_pr_file_categorize_laravel_paths(self):
        """Test that Laravel-specific paths are categorized as backend (~7% usage)."""
        # Laravel HTTP layer
        self.assertEqual(PRFile.categorize_file("app/Http/Controllers/UserController.php"), "backend")
        self.assertEqual(PRFile.categorize_file("app/Http/Middleware/Auth.php"), "backend")
        # Laravel Eloquent models
        self.assertEqual(PRFile.categorize_file("app/Models/User.php"), "backend")
        # Laravel Jobs
        self.assertEqual(PRFile.categorize_file("app/Jobs/ProcessOrder.php"), "backend")
        # Laravel database factories
        self.assertEqual(PRFile.categorize_file("database/factories/UserFactory.php"), "backend")

    def test_pr_file_categorize_nestjs_paths(self):
        """Test that NestJS-specific paths are categorized as backend (~6% usage)."""
        # NestJS modules
        self.assertEqual(PRFile.categorize_file("src/modules/auth/auth.module.ts"), "backend")
        # NestJS guards
        self.assertEqual(PRFile.categorize_file("src/guards/jwt.guard.ts"), "backend")
        # NestJS interceptors
        self.assertEqual(PRFile.categorize_file("src/interceptors/logging.interceptor.ts"), "backend")
        # NestJS decorators
        self.assertEqual(PRFile.categorize_file("src/decorators/user.decorator.ts"), "backend")

    def test_pr_file_categorize_spring_boot_paths(self):
        """Test that Spring Boot-specific paths are categorized as backend (~9% usage)."""
        # Spring controllers (singular)
        self.assertEqual(PRFile.categorize_file("src/main/java/com/app/controller/UserController.java"), "backend")
        # Spring Data repositories (singular)
        self.assertEqual(PRFile.categorize_file("src/main/java/com/app/repository/UserRepository.java"), "backend")
        # JPA entities
        self.assertEqual(PRFile.categorize_file("src/main/java/com/app/entity/User.java"), "backend")

    def test_pr_file_categorize_phoenix_paths(self):
        """Test that Phoenix-specific paths are categorized as backend (~3% usage)."""
        # Phoenix web directory
        self.assertEqual(PRFile.categorize_file("lib/my_app_web/controllers/page_controller.ex"), "backend")
        # Phoenix LiveView
        self.assertEqual(PRFile.categorize_file("lib/my_app_web/live/dashboard_live.ex"), "backend")
        # Phoenix channels
        self.assertEqual(PRFile.categorize_file("lib/my_app_web/channels/room_channel.ex"), "backend")
        # Phoenix plugs
        self.assertEqual(PRFile.categorize_file("lib/my_app_web/plugs/auth.ex"), "backend")

    def test_pr_file_categorize_aspnet_paths(self):
        """Test that ASP.NET-specific paths are categorized as backend (~14% usage)."""
        # ASP.NET Controllers (PascalCase)
        self.assertEqual(PRFile.categorize_file("Controllers/UserController.cs"), "backend")
        # ASP.NET ViewModels
        self.assertEqual(PRFile.categorize_file("ViewModels/UserViewModel.cs"), "backend")
        # EF Core Data context
        self.assertEqual(PRFile.categorize_file("Data/ApplicationDbContext.cs"), "backend")

    def test_pr_file_categorize_rails_paths(self):
        """Test that Rails-specific paths are categorized as backend (~3% usage)."""
        # Rails controllers
        self.assertEqual(PRFile.categorize_file("app/controllers/users_controller.rb"), "backend")
        # Rails models
        self.assertEqual(PRFile.categorize_file("app/models/user.rb"), "backend")
        # Rails jobs (ActiveJob)
        self.assertEqual(PRFile.categorize_file("app/jobs/process_order_job.rb"), "backend")
        # Rails mailers
        self.assertEqual(PRFile.categorize_file("app/mailers/user_mailer.rb"), "backend")

    def test_pr_file_categorize_vue_frontend_paths(self):
        """Test that Vue.js-specific paths are categorized as frontend (~12% usage)."""
        # Vue composables
        self.assertEqual(PRFile.categorize_file("src/composables/useAuth.ts"), "frontend")
        # Pinia stores
        self.assertEqual(PRFile.categorize_file("src/pinia/userStore.ts"), "frontend")
        # Vuex stores
        self.assertEqual(PRFile.categorize_file("src/vuex/modules/cart.js"), "frontend")

    def test_pr_file_categorize_angular_frontend_paths(self):
        """Test that Angular-specific frontend paths are categorized correctly (~11% usage)."""
        # Angular guards (frontend route guards)
        self.assertEqual(PRFile.categorize_file("src/app/guards/auth.guard.ts"), "frontend")
        # Angular pipes
        self.assertEqual(PRFile.categorize_file("src/app/pipes/currency.pipe.ts"), "frontend")
        # Angular directives
        self.assertEqual(PRFile.categorize_file("src/app/directives/highlight.directive.ts"), "frontend")
