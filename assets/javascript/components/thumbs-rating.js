/**
 * Thumbs Rating Alpine Component
 *
 * Reusable feedback UI for LLM-generated content.
 * Registers with Alpine.data() for proper HTMX compatibility.
 *
 * Usage in templates:
 *   <div x-data="thumbsRating"
 *        data-content-type="engineering_insight"
 *        data-content-id="123"
 *        data-snapshot='{"headline":"..."}'>
 */

/**
 * Register the thumbsRating Alpine component
 * Call this during alpine:init
 */
export function registerThumbsRating() {
  if (!window.Alpine) {
    console.warn('Alpine not found, skipping thumbsRating registration');
    return;
  }

  window.Alpine.data('thumbsRating', () => ({
    rating: null,
    loading: false,
    showComment: false,
    commentSaved: false,

    // Config from data attributes
    contentType: '',
    contentId: '',
    snapshot: null,
    inputContext: null,
    promptVersion: '',
    feedbackUrl: '',

    init() {
      // Read config from data attributes on the element
      const el = this.$el;
      this.contentType = el.dataset.contentType || '';
      this.contentId = el.dataset.contentId || '';
      this.feedbackUrl = el.dataset.feedbackUrl || '';
      this.promptVersion = el.dataset.promptVersion || '';

      // Parse JSON data attributes
      try {
        this.snapshot = el.dataset.snapshot ? JSON.parse(el.dataset.snapshot) : null;
      } catch (e) {
        console.warn('Failed to parse snapshot:', e);
        this.snapshot = null;
      }

      try {
        this.inputContext = el.dataset.inputContext ? JSON.parse(el.dataset.inputContext) : null;
      } catch (e) {
        console.warn('Failed to parse inputContext:', e);
        this.inputContext = null;
      }

      // Load existing feedback state if available
      this.loadExistingFeedback();
    },

    async loadExistingFeedback() {
      if (!this.contentType || !this.contentId) return;

      // Build the get URL from the submit URL
      // Submit URL: /app/feedback/llm/submit/
      // Get URL: /app/feedback/llm/{content_type}/{content_id}/
      const baseUrl = this.feedbackUrl.replace('/submit/', `/${this.contentType}/${this.contentId}/`);

      try {
        const response = await fetch(baseUrl, {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          if (data.rating !== null && data.rating !== undefined) {
            this.rating = data.rating ? 'up' : 'down';
            // Check if there's a comment saved
            if (data.comment) {
              this.commentSaved = true;
            }
          }
        }
      } catch (error) {
        // Silently fail - user just won't see their previous rating
        console.debug('Could not load existing feedback:', error);
      }
    },

    async submitRating(isPositive) {
      if (this.loading) return;

      this.loading = true;
      try {
        // Get CSRF token from cookie or hidden input
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
          || document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1]
          || '';

        const payload = {
          content_type: this.contentType,
          content_id: this.contentId,
          rating: isPositive,
          content_snapshot: this.snapshot,
        };

        if (this.inputContext) {
          payload.input_context = this.inputContext;
        }
        if (this.promptVersion) {
          payload.prompt_version = this.promptVersion;
        }

        const response = await fetch(this.feedbackUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify(payload)
        });

        if (response.ok) {
          this.rating = isPositive ? 'up' : 'down';
          this.showComment = true;
          this.commentSaved = false;
        } else {
          console.error('Feedback submission failed:', response.status);
        }
      } catch (error) {
        console.error('Feedback submission error:', error);
      } finally {
        this.loading = false;
      }
    },

    openFeedbackModal() {
      this.$dispatch('open-feedback-modal', {
        contentType: this.contentType,
        contentId: this.contentId
      });
    }
  }));
}
