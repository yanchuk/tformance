/**
 * Date Range Picker Alpine Component
 *
 * This component works with the dateRange store to provide a UI
 * for selecting date ranges. The store persists state across HTMX
 * swaps while this component handles UI-specific concerns.
 */

/**
 * Register the dateRangePicker Alpine component
 * Call this during alpine:init
 */
export function registerDateRangePicker() {
  if (!window.Alpine) {
    console.warn('Alpine not found, skipping dateRangePicker registration');
    return;
  }

  window.Alpine.data('dateRangePicker', (initialDays = 30, initialStart = '', initialEnd = '', initialPreset = '') => ({
    // UI-only state (not shared across HTMX swaps)
    showCustom: false,
    today: new Date().toISOString().split('T')[0],

    // Translations (injected from template)
    labels: {
      last12Months: 'Last 12 Months',
      thisYear: 'This Year',
      lastYear: 'Last Year',
      thisQuarter: 'This Quarter',
      yoy: 'YoY',
      custom: 'Custom',
      more: 'More'
    },

    init() {
      // Sync store from URL on component init
      // Store may already be synced, but ensure it matches current URL
      const store = this.$store.dateRange;
      const params = new URLSearchParams(window.location.search);

      if (params.has('days')) {
        store.days = parseInt(params.get('days')) || 30;
        store.preset = '';
      } else if (params.has('preset')) {
        store.preset = params.get('preset');
        store.days = 0;
      } else if (params.has('start') && params.has('end')) {
        store.customStart = params.get('start');
        store.customEnd = params.get('end');
        store.days = 0;
        store.preset = 'custom';
      }
    },

    // Convenience getters that delegate to store
    get days() {
      return this.$store.dateRange.days;
    },

    get preset() {
      return this.$store.dateRange.preset;
    },

    get customStart() {
      return this.$store.dateRange.customStart;
    },
    set customStart(val) {
      this.$store.dateRange.customStart = val;
    },

    get customEnd() {
      return this.$store.dateRange.customEnd;
    },
    set customEnd(val) {
      this.$store.dateRange.customEnd = val;
    },

    isActive(d) {
      return this.$store.dateRange.isActive(d);
    },

    isPresetActive() {
      return this.$store.dateRange.isPresetActive() ||
             (this.$store.dateRange.customStart && this.$store.dateRange.customEnd);
    },

    getActiveLabel() {
      const store = this.$store.dateRange;
      if (store.preset === '12_months') return this.labels.last12Months;
      if (store.preset === 'this_year') return this.labels.thisYear;
      if (store.preset === 'last_year') return this.labels.lastYear;
      if (store.preset === 'this_quarter') return this.labels.thisQuarter;
      if (store.preset === 'yoy') return this.labels.yoy;
      if (store.preset === 'custom' || (store.customStart && store.customEnd)) {
        return this.labels.custom;
      }
      return this.labels.more;
    },

    showDateRange() {
      const store = this.$store.dateRange;
      return store.preset || (store.customStart && store.customEnd);
    },

    formatDateRange() {
      const store = this.$store.dateRange;
      if (store.customStart && store.customEnd) {
        return `${store.customStart} - ${store.customEnd}`;
      }
      if (store.preset === '12_months') {
        const now = new Date();
        const start = new Date(now);
        start.setDate(start.getDate() - 365);
        return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} - Today`;
      }
      if (store.preset === 'this_year') {
        const year = new Date().getFullYear();
        return `Jan 1, ${year} - Today`;
      }
      if (store.preset === 'last_year') {
        const year = new Date().getFullYear() - 1;
        return `Jan 1, ${year} - Dec 31, ${year}`;
      }
      if (store.preset === 'this_quarter') {
        const now = new Date();
        const quarter = Math.floor(now.getMonth() / 3);
        const quarterStart = new Date(now.getFullYear(), quarter * 3, 1);
        return `${quarterStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - Today`;
      }
      return '';
    },

    setDays(d) {
      this.$store.dateRange.setDays(d);
      this.navigate({ days: d });
    },

    setPreset(p) {
      this.$store.dateRange.setPreset(p);
      this.navigate({ preset: p });
    },

    applyCustomRange() {
      const store = this.$store.dateRange;
      if (store.customStart && store.customEnd) {
        store.setCustomRange(store.customStart, store.customEnd);
        this.$refs.customModal.close();
        this.navigate({ start: store.customStart, end: store.customEnd });
      }
    },

    navigate(newParams) {
      // Preserve existing params like granularity and metrics
      const params = new URLSearchParams(window.location.search);

      // Clear conflicting date params when setting new ones
      if (newParams.days) {
        params.delete('preset');
        params.delete('start');
        params.delete('end');
        params.set('days', newParams.days);
      } else if (newParams.preset) {
        params.delete('days');
        params.delete('start');
        params.delete('end');
        params.set('preset', newParams.preset);
      } else if (newParams.start && newParams.end) {
        params.delete('days');
        params.delete('preset');
        params.set('start', newParams.start);
        params.set('end', newParams.end);
      }

      // Build URL with preserved params
      const url = window.location.pathname + '?' + params.toString();
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
