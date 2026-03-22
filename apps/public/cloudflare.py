"""Cloudflare cache purge utility.

Purges all cached content after daily stats computation so visitors
see fresh data. Fire-and-forget: failures are logged but don't
block the pipeline (cache expires naturally at 12h TTL).

Requires env vars:
  CLOUDFLARE_API_TOKEN — scoped to Zone.Cache Purge permission
  CLOUDFLARE_ZONE_ID   — zone identifier for tformance.com
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


def purge_all_cache():
    """Purge all Cloudflare cache for the zone.

    Returns True on success, False on failure or if not configured.
    """
    api_token = getattr(settings, "CLOUDFLARE_API_TOKEN", None)
    zone_id = getattr(settings, "CLOUDFLARE_ZONE_ID", None)

    if not api_token or not zone_id:
        logger.info("Cloudflare cache purge skipped: credentials not configured")
        return False

    url = f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/purge_cache"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {"purge_everything": True}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()

        if response.ok and data.get("success"):
            logger.info("Cloudflare cache purged successfully")
            return True
        else:
            errors = data.get("errors", [])
            logger.warning(f"Cloudflare cache purge failed: {errors}")
            return False

    except requests.RequestException:
        logger.exception("Cloudflare cache purge request failed")
        return False
