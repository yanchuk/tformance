import htmx from "htmx.org";
import "htmx-ext-ws";

// Make htmx globally available
window.htmx = htmx;

// Debug: confirm module initialization
console.log('[htmx.js] Module loaded, htmx version:', htmx.version || 'unknown');
window.__htmxErrorHandlerLoaded = true;

// Debug: also listen via document.body to compare with htmx.on()
// Use window since body might not exist yet
window.addEventListener('htmx:afterRequest', function(evt) {
  console.log('[htmx.js] Window htmx:afterRequest fired!', {
    failed: evt.detail?.failed,
    successful: evt.detail?.successful,
  });
});

/**
 * Global HTMX Error Handling
 *
 * Handles failed HTMX requests by:
 * 1. Logging errors to console for debugging
 * 2. Replacing loading spinners with user-friendly error messages
 * 3. Providing a retry mechanism
 *
 * Uses safe DOM methods (createElement, textContent) - no innerHTML.
 */

/**
 * Create an error message element using safe DOM methods
 * @param {string} message - The error message to display
 * @param {string} retryUrl - Optional URL for retry button
 * @returns {HTMLElement} The error element
 */
function createErrorElement(message, retryUrl) {
  const container = document.createElement('div');
  container.className = 'alert alert-error flex flex-col gap-2 p-4';
  container.setAttribute('role', 'alert');
  container.setAttribute('data-htmx-error', 'true');

  // Error icon and message row
  const messageRow = document.createElement('div');
  messageRow.className = 'flex items-center gap-2';

  const icon = document.createElement('svg');
  icon.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  icon.setAttribute('class', 'h-5 w-5 flex-shrink-0');
  icon.setAttribute('fill', 'none');
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.setAttribute('stroke', 'currentColor');
  const iconPath = document.createElement('path');
  iconPath.setAttribute('stroke-linecap', 'round');
  iconPath.setAttribute('stroke-linejoin', 'round');
  iconPath.setAttribute('stroke-width', '2');
  iconPath.setAttribute('d', 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z');
  icon.appendChild(iconPath);

  const text = document.createElement('span');
  text.textContent = message;

  messageRow.appendChild(icon);
  messageRow.appendChild(text);
  container.appendChild(messageRow);

  // Retry button row
  const buttonRow = document.createElement('div');
  buttonRow.className = 'flex gap-2';

  const retryButton = document.createElement('button');
  retryButton.type = 'button';
  retryButton.className = 'btn btn-sm btn-ghost';
  retryButton.textContent = 'Retry';
  retryButton.addEventListener('click', () => {
    if (retryUrl) {
      // Re-trigger the HTMX request
      const target = container.parentElement;
      if (target && window.htmx) {
        htmx.ajax('GET', retryUrl, { target: target, swap: 'innerHTML' });
      }
    } else {
      // Fallback: reload the page
      window.location.reload();
    }
  });

  const reloadButton = document.createElement('button');
  reloadButton.type = 'button';
  reloadButton.className = 'btn btn-sm btn-ghost';
  reloadButton.textContent = 'Reload Page';
  reloadButton.addEventListener('click', () => {
    window.location.reload();
  });

  buttonRow.appendChild(retryButton);
  buttonRow.appendChild(reloadButton);
  container.appendChild(buttonRow);

  return container;
}

/**
 * Handle HTMX response errors (4xx, 5xx)
 * Using htmx:afterRequest which fires after every request
 */
console.log('[htmx.js] Registering htmx:afterRequest handler');
htmx.on('htmx:afterRequest', function(evt) {
  console.log('[htmx.js] htmx:afterRequest fired:', {
    failed: evt.detail.failed,
    successful: evt.detail.successful,
    status: evt.detail.xhr?.status,
  });
  // Only handle failed requests
  if (!evt.detail.failed) return;

  const xhr = evt.detail.xhr;
  const target = evt.detail.target || evt.detail.elt;
  const requestPath = evt.detail.pathInfo?.requestPath || evt.detail.requestConfig?.path || '';

  // Log for debugging
  console.error('HTMX request failed:', {
    status: xhr?.status,
    statusText: xhr?.statusText,
    url: requestPath,
    targetId: target?.id || 'no-id',
    targetTagName: target?.tagName || 'no-tag',
    hasTarget: !!target,
  });

  // Replace target content with error message
  if (target) {
    const status = xhr?.status || 0;
    const errorMessage = status === 404
      ? 'Content not found. Please try again.'
      : status >= 500
        ? 'Server error. Please try again later.'
        : 'Failed to load content. Please try again.';

    try {
      const errorElement = createErrorElement(errorMessage, requestPath);
      console.error('HTMX replacing content in:', target.id || target.tagName);
      // Clear target and add error
      target.replaceChildren(errorElement);
      console.error('HTMX content replaced successfully');
    } catch (err) {
      console.error('HTMX error handler failed:', err);
    }
  } else {
    console.error('HTMX no target element found for error handling');
  }
});

/**
 * Handle HTMX send errors (network failures, CORS, etc.)
 */
htmx.on('htmx:sendError', function(evt) {
  const target = evt.detail.target;
  const requestPath = evt.detail.pathInfo?.requestPath || '';

  // Log for debugging
  console.error('HTMX network error:', {
    url: requestPath,
    target: target?.id || 'unknown',
    error: 'Network request failed - possible network issue or CORS error',
  });

  // Replace target content with error message
  if (target) {
    const errorElement = createErrorElement(
      'Network error. Please check your connection and try again.',
      requestPath
    );

    target.replaceChildren(errorElement);
  }
});

/**
 * Re-initialize Alpine.js components after HTMX swap
 * This ensures Alpine components in swapped content work properly
 */
htmx.on('htmx:afterSwap', function(evt) {
  if (window.Alpine && evt.detail.target) {
    // Initialize Alpine on the newly swapped content
    window.Alpine.initTree(evt.detail.target);
  }
});

/**
 * Re-initialize Alpine.js components after OOB (Out-of-Band) swap
 * OOB swaps replace elements outside the main swap target and need
 * their own Alpine initialization to enable reactive bindings
 */
htmx.on('htmx:oobAfterSwap', function(evt) {
  if (window.Alpine && evt.detail.target) {
    // Initialize Alpine on the OOB-swapped element
    window.Alpine.initTree(evt.detail.target);

    // Also sync dateRange store from URL if the date picker was swapped
    if (evt.detail.target.id === 'date-range-picker-container') {
      const store = window.Alpine.store('dateRange');
      if (store && store.syncFromUrl) {
        store.syncFromUrl();
      }
    }
  }
});
