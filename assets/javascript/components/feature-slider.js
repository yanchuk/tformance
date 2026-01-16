/**
 * Feature Showcase Slider Component
 *
 * An accessible, auto-rotating feature slider using requestAnimationFrame
 * for smooth progress animation (best practice per Alpine.js community).
 *
 * Features:
 * - requestAnimationFrame-based timing for smooth 60fps progress bar
 * - Preloads images for seamless transitions
 * - Respects prefers-reduced-motion
 * - Full keyboard navigation (arrows, home, end)
 * - ARIA support for screen readers
 * - Pause on hover/focus
 */
export function registerFeatureSlider() {
  if (!window.Alpine) {
    console.warn('Alpine not found, skipping featureSlider registration');
    return;
  }

  window.Alpine.data('featureSlider', () => ({
    slides: [],
    currentSlide: 0,
    isPaused: false,
    progress: 0,
    duration: 5000, // 5 seconds per slide
    firstFrameTime: 0,
    animationFrame: null,
    reducedMotion: false,

    init() {
      // Parse slides from data attribute
      try {
        this.slides = this.$el.dataset.slides
          ? JSON.parse(this.$el.dataset.slides)
          : [];
      } catch (e) {
        console.warn('Failed to parse feature slides:', e);
        this.slides = [];
      }

      if (this.slides.length === 0) return;

      // Check for reduced motion preference
      this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      // Preload all images for smooth transitions
      this.preloadImages();

      // Start autoplay unless reduced motion is preferred
      if (!this.reducedMotion && this.slides.length > 1) {
        this.startAnimation();
      }

      // Watch for slide changes to restart animation
      this.$watch('currentSlide', () => {
        if (!this.reducedMotion && this.slides.length > 1) {
          this.cancelAnimation();
          this.startAnimation();
        }
      });
    },

    preloadImages() {
      this.slides.forEach(slide => {
        if (slide.image) {
          const img = new Image();
          img.src = slide.image;
        }
      });
    },

    startAnimation() {
      this.progress = 0;
      this.firstFrameTime = performance.now();
      this.animationFrame = requestAnimationFrame(this.animate.bind(this));
    },

    animate(now) {
      // Skip if paused
      if (this.isPaused) {
        // Store pause time to resume from same progress
        this.animationFrame = requestAnimationFrame(this.animate.bind(this));
        return;
      }

      const elapsed = now - this.firstFrameTime;
      const timeFraction = elapsed / this.duration;

      if (timeFraction <= 1) {
        this.progress = timeFraction * 100;
        this.animationFrame = requestAnimationFrame(this.animate.bind(this));
      } else {
        // Move to next slide
        this.currentSlide = (this.currentSlide + 1) % this.slides.length;
        // Animation will restart via $watch
      }
    },

    cancelAnimation() {
      if (this.animationFrame) {
        cancelAnimationFrame(this.animationFrame);
        this.animationFrame = null;
      }
    },

    next() {
      this.currentSlide = (this.currentSlide + 1) % this.slides.length;
    },

    prev() {
      this.currentSlide = (this.currentSlide - 1 + this.slides.length) % this.slides.length;
    },

    goToSlide(index) {
      if (index >= 0 && index < this.slides.length && index !== this.currentSlide) {
        this.currentSlide = index;
      }
    },

    pauseAutoplay() {
      this.isPaused = true;
      // Adjust firstFrameTime to account for pause duration when resuming
      this.pauseTime = performance.now();
    },

    resumeAutoplay() {
      if (this.isPaused && this.pauseTime) {
        // Offset firstFrameTime by pause duration to resume from same progress
        const pauseDuration = performance.now() - this.pauseTime;
        this.firstFrameTime += pauseDuration;
      }
      this.isPaused = false;
    },

    handleKeydown(event) {
      // Save scroll position before slide change to prevent browser auto-scroll
      const scrollY = window.scrollY;
      let handled = false;

      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          this.prev();
          handled = true;
          break;
        case 'ArrowRight':
          event.preventDefault();
          this.next();
          handled = true;
          break;
        case 'Home':
          event.preventDefault();
          this.goToSlide(0);
          handled = true;
          break;
        case 'End':
          event.preventDefault();
          this.goToSlide(this.slides.length - 1);
          handled = true;
          break;
      }

      // Restore scroll position after DOM updates to prevent focus-scroll
      // Use setTimeout to ensure it runs after browser's focus-scroll
      if (handled) {
        setTimeout(() => {
          window.scrollTo({ top: scrollY, behavior: 'instant' });
        }, 0);
      }
    },

    destroy() {
      this.cancelAnimation();
    }
  }));
}
