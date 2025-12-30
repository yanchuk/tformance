/**
 * Repository Selector Alpine Component
 *
 * This component works with the repoFilter store to provide a UI
 * for selecting repositories. The store persists state across HTMX
 * swaps while this component handles UI-specific concerns.
 */

/**
 * Register the repoSelector Alpine component
 * Call this during alpine:init
 */
export function registerRepoSelector() {
  if (!window.Alpine) {
    console.warn('Alpine not found, skipping repoSelector registration');
    return;
  }

  window.Alpine.data('repoSelector', (initialRepos = []) => ({
    // UI-only state
    open: false,
    searchQuery: '',

    init() {
      // Set available repos from template data
      if (initialRepos && initialRepos.length > 0) {
        this.$store.repoFilter.setRepos(initialRepos);
      }

      // Sync from URL on init
      this.$store.repoFilter.syncFromUrl();
    },

    // Convenience getters
    get selectedRepo() {
      return this.$store.repoFilter.selectedRepo;
    },

    get repos() {
      return this.$store.repoFilter.repos;
    },

    get filteredRepos() {
      if (!this.searchQuery) {
        return this.repos;
      }
      const query = this.searchQuery.toLowerCase();
      return this.repos.filter(repo =>
        repo.toLowerCase().includes(query)
      );
    },

    isAll() {
      return this.$store.repoFilter.isAll();
    },

    isSelected(repo) {
      return this.$store.repoFilter.isSelected(repo);
    },

    getDisplayName() {
      return this.$store.repoFilter.getDisplayName();
    },

    /**
     * Get short name for a repo (without owner prefix)
     */
    getShortName(repo) {
      const parts = repo.split('/');
      return parts.length > 1 ? parts[1] : repo;
    },

    /**
     * Select a repository and navigate
     */
    selectRepo(repo) {
      this.$store.repoFilter.setRepo(repo);
      this.open = false;
      this.searchQuery = '';
      this.navigate();
    },

    /**
     * Select "All Repositories" and navigate
     */
    selectAll() {
      this.$store.repoFilter.setRepo('');
      this.open = false;
      this.searchQuery = '';
      this.navigate();
    },

    /**
     * Toggle dropdown
     */
    toggle() {
      this.open = !this.open;
      if (!this.open) {
        this.searchQuery = '';
      }
    },

    /**
     * Close dropdown
     */
    close() {
      this.open = false;
      this.searchQuery = '';
    },

    /**
     * Navigate to the current page with updated repo filter
     */
    navigate() {
      const params = new URLSearchParams(window.location.search);

      // Update or remove repo param
      if (this.selectedRepo) {
        params.set('repo', this.selectedRepo);
      } else {
        params.delete('repo');
      }

      // Build URL with preserved params
      const queryString = params.toString();
      const url = window.location.pathname + (queryString ? '?' + queryString : '');
      const target = document.getElementById('page-content');

      if (target && window.htmx) {
        // Update browser URL first
        history.pushState({}, '', url);
        // Then update content via HTMX
        htmx.ajax('GET', url, {
          target: target,
          swap: 'outerHTML'
        });
      } else {
        // Fallback to regular navigation
        window.location.href = url;
      }
    }
  }));
}
