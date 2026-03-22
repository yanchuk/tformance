"""Constants for public proof surfaces.

Centralized CTA text, freshness copy, and correlation thresholds.
Injected into templates via context processor so views never hardcode these strings.
"""

# Primary conversion CTA — used on every canonical page
PRIMARY_CTA_TEXT = "See Your Team's Benchmarks"

# Secondary CTA — used in methodology/footer sections
SECONDARY_CTA_TEXT = "Book Demo"

# Freshness copy — explains data source
FRESHNESS_COPY = "Updated daily from public GitHub pull requests."

# Correlation classification thresholds
CORRELATION_STRONG_NEGATIVE = -0.6
CORRELATION_MODERATE_NEGATIVE = -0.3
CORRELATION_MODERATE_POSITIVE = 0.3
CORRELATION_STRONG_POSITIVE = 0.6

# Minimum weekly buckets required for correlation
MIN_CORRELATION_WEEKS = 6
