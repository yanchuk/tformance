import Alpine from 'alpinejs';
import { registerDateRangePicker } from './components/date-range-picker.js';

/**
 * Alpine.js Stores
 *
 * These stores persist state across HTMX content swaps.
 * Local x-data state is destroyed when HTMX replaces elements,
 * but stores survive because they're on the Alpine global object.
 */

// Initialize stores before Alpine starts
document.addEventListener('alpine:init', () => {
  /**
   * Date Range Store
   * Manages the selected time range for analytics pages
   */
  Alpine.store('dateRange', {
    days: 30,
    preset: '',
    granularity: 'weekly',
    customStart: '',
    customEnd: '',

    /**
     * Set days and clear preset (for 7d, 30d, 90d buttons)
     */
    setDays(d) {
      this.days = d;
      this.preset = '';
      this.customStart = '';
      this.customEnd = '';
    },

    /**
     * Set preset and clear days (for This Year, Last Year, etc)
     */
    setPreset(p) {
      this.preset = p;
      this.days = 0;
      this.customStart = '';
      this.customEnd = '';
    },

    /**
     * Set custom date range
     */
    setCustomRange(start, end) {
      this.customStart = start;
      this.customEnd = end;
      this.preset = 'custom';
      this.days = 0;
    },

    /**
     * Set granularity (weekly, monthly)
     */
    setGranularity(g) {
      this.granularity = g;
    },

    /**
     * Check if a specific days value is active
     */
    isActive(d) {
      return this.days === d && !this.preset;
    },

    /**
     * Check if any preset is active
     */
    isPresetActive() {
      return !!this.preset;
    },

    /**
     * Sync from URL params (call on page load)
     */
    syncFromUrl() {
      const params = new URLSearchParams(window.location.search);
      if (params.has('days')) {
        this.days = parseInt(params.get('days')) || 30;
        this.preset = '';
      }
      if (params.has('preset')) {
        this.preset = params.get('preset');
        this.days = 0;
      }
      if (params.has('start') && params.has('end')) {
        this.customStart = params.get('start');
        this.customEnd = params.get('end');
        this.preset = 'custom';
        this.days = 0;
      }
      if (params.has('granularity')) {
        this.granularity = params.get('granularity');
      }
    },

    /**
     * Build URL params for navigation
     */
    toUrlParams() {
      const params = new URLSearchParams();
      if (this.preset === 'custom' && this.customStart && this.customEnd) {
        params.set('start', this.customStart);
        params.set('end', this.customEnd);
      } else if (this.preset) {
        params.set('preset', this.preset);
      } else {
        params.set('days', this.days.toString());
      }
      if (this.granularity && this.granularity !== 'weekly') {
        params.set('granularity', this.granularity);
      }
      return params.toString();
    }
  });

  /**
   * Metrics Store
   * Manages selected metrics for comparison views
   */
  Alpine.store('metrics', {
    selected: [],
    maxMetrics: 3,

    /**
     * Toggle a metric selection
     * Uses immutable operations for proper Alpine.js reactivity
     */
    toggle(metric) {
      const index = this.selected.indexOf(metric);
      if (index > -1) {
        // Use filter() for proper reactivity (creates new array reference)
        this.selected = this.selected.filter((_, i) => i !== index);
      } else if (this.selected.length < this.maxMetrics) {
        // Use spread for proper reactivity (creates new array reference)
        this.selected = [...this.selected, metric];
      }
    },

    /**
     * Check if a metric is selected
     */
    isSelected(metric) {
      return this.selected.includes(metric);
    },

    /**
     * Clear all selections
     */
    clear() {
      this.selected = [];
    },

    /**
     * Check if max metrics reached
     */
    isMaxReached() {
      return this.selected.length >= this.maxMetrics;
    }
  });

  // Sync dateRange store from URL on init
  Alpine.store('dateRange').syncFromUrl();

  // Register reusable Alpine components
  registerDateRangePicker();
});

// Expose Alpine globally
window.Alpine = Alpine;

// Start Alpine after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  Alpine.start();
});
