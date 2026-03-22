"""
adblocker.py — Simple domain-based ad/tracker blocker for Orbit.
Uses _StealthInterceptor extension pattern from webview.py.
"""
from __future__ import annotations

# Domains to block (ads, trackers, telemetry)
_BLOCK_DOMAINS = {
    'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
    'adservice.google.com', 'ads.google.com', 'adnxs.com', 'outbrain.com',
    'taboola.com', 'criteo.com', 'criteo.net', 'amazon-adsystem.com',
    'media.net', 'adsrvr.org', 'rubiconproject.com', 'pubmatic.com',
    'openx.net', 'appnexus.com', 'turn.com', 'advertising.com',
    'moatads.com', 'scorecardresearch.com', 'quantserve.com',
    'zedo.com', 'tribalfusion.com', 'advertising.yahoo.com',
    # Trackers
    'google-analytics.com', 'googletagmanager.com', 'googletagservices.com',
    'hotjar.com', 'mixpanel.com', 'segment.com', 'segment.io',
    'amplitude.com', 'heapanalytics.com', 'fullstory.com', 'logrocket.com',
    'mouseflow.com', 'crazyegg.com', 'clicktale.net', 'inspectlet.com',
    'intercom.io', 'intercomcdn.com', 'drift.com', 'driftt.com',
    'facebook.com/tr', 'connect.facebook.net', 'bat.bing.com',
    'ads.twitter.com', 'analytics.twitter.com', 'static.ads-twitter.com',
    'platform.twitter.com',
}


def is_blocked(url: str) -> bool:
    """Return True if the URL should be blocked."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ''
        # Check if host or any parent domain is in block list
        parts = host.split('.')
        for i in range(len(parts) - 1):
            domain = '.'.join(parts[i:])
            if domain in _BLOCK_DOMAINS:
                return True
    except Exception:
        pass
    return False
