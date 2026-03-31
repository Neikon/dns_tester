# provider_icons.py
#
# Resolve sidebar icon names for known DNS providers.

from __future__ import annotations

# Installed provider icons stay namespaced to avoid collisions with theme icons,
# but the selection logic derives them directly from the provider name.
_PROVIDER_ICON_PREFIX = "es.neikon.dns_tester-provider-"
_KNOWN_PROVIDER_ICON_SLUGS = {
    "adguard",
    "appliedprivacy",
    "cloudflare",
    "cleanbrowsing",
    "comodosecuredns",
    "controld",
    "dns4eu",
    "flashstart",
    "gcore",
    "google",
    "mullvad",
    "nextdns",
    "opendns",
    "quad9",
}

# Unknown or user-defined providers keep a generic network glyph in the sidebar.
FALLBACK_PROVIDER_ICON_NAME = "network-server-symbolic"


def _provider_icon_slug(provider_name: str) -> str:
    """Collapse a provider label into the icon slug used in the icon theme."""
    return "".join(character for character in provider_name.lower() if character.isalnum())


def get_provider_icon_name(provider_name: str) -> str:
    """Return the themed icon name used for one provider sidebar item."""
    provider_slug = _provider_icon_slug(provider_name)
    if provider_slug not in _KNOWN_PROVIDER_ICON_SLUGS:
        return FALLBACK_PROVIDER_ICON_NAME
    return f"{_PROVIDER_ICON_PREFIX}{provider_slug}"
