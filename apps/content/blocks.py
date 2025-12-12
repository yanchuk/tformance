import bleach
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from wagtail.blocks import TextBlock

# Safe HTML tags and attributes for caption content
ALLOWED_TAGS = ["a", "b", "i", "em", "strong", "br", "span"]
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "target", "rel"]}


class CaptionBlock(TextBlock):
    """
    A block for generating <figcaptions> that can also use html characters (so you can add, e.g. links).

    HTML content is sanitized using bleach to prevent XSS attacks while allowing
    safe tags like links, bold, italic, etc.
    """

    def render_basic(self, value, context=None):
        if value:
            # Sanitize HTML to prevent XSS while allowing safe tags
            sanitized = bleach.clean(
                value,
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                strip=True,
            )
            return format_html("<figcaption>{0}</figcaption>", mark_safe(sanitized))
        else:
            return ""

    class Meta:
        icon = "info-circle"
