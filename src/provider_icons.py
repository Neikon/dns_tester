# provider_icons.py
#
# Resolve sidebar icon names for known DNS providers.

from __future__ import annotations

# Bundled providers use dedicated themed icons installed with the application.
_PROVIDER_ICON_NAMES = {
    "AdGuard": "es.neikon.dns_tester-provider-adguard",
    "Cloudflare": "es.neikon.dns_tester-provider-cloudflare",
    "ControlD": "es.neikon.dns_tester-provider-controld",
    "DNS4EU": "es.neikon.dns_tester-provider-dns4eu",
    "FlashStart": "es.neikon.dns_tester-provider-flashstart",
    "Gcore": "es.neikon.dns_tester-provider-gcore",
    "Google": "es.neikon.dns_tester-provider-google",
    "Mullvad": "es.neikon.dns_tester-provider-mullvad",
    "NextDNS": "es.neikon.dns_tester-provider-nextdns",
    "Quad9": "es.neikon.dns_tester-provider-quad9",
}

# Unknown or user-defined providers keep a generic network glyph in the sidebar.
FALLBACK_PROVIDER_ICON_NAME = "network-server-symbolic"


def get_provider_icon_name(provider_name: str) -> str:
    """Return the themed icon name used for one provider sidebar item."""
    return _PROVIDER_ICON_NAMES.get(provider_name, FALLBACK_PROVIDER_ICON_NAME)
