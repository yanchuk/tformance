from django.utils.html import format_html
from django.utils.safestring import mark_safe
from wagtail.blocks import TextBlock

from apps.utils.sanitization import sanitize_html


class CaptionBlock(TextBlock):
    """
    A block for generating <figcaptions> that can also use html characters (so you can add, e.g. links).

    HTML content is sanitized using bleach to prevent XSS attacks while allowing
    safe tags like links, bold, italic, etc.
    """

    def render_basic(self, value, context=None):
        if value:
            sanitized = sanitize_html(value)
            return format_html("<figcaption>{0}</figcaption>", mark_safe(sanitized))
        else:
            return ""

    class Meta:
        icon = "info-circle"
