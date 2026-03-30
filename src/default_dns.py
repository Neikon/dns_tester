# default_dns.py
#
# Default DNS entries shipped with the application.
# Keep values in English and only include resolvers that work out of the box.

from __future__ import annotations

from typing import TypedDict


class DefaultDnsEntry(TypedDict):
    """Structure used by the bundled DNS catalog."""

    id: str
    name: str
    regions: list[str]
    target: str
    transport: str
    tls_hostname: str | None
    doh_method: str


# Bundled resolver entries use stable IDs so users can hide a default entry permanently.
DEFAULT_DNS: list[DefaultDnsEntry] = [
    {
        "id": "cloudflare-do53",
        "name": "Cloudflare (Do53)",
        "regions": ["US"],
        "target": "1.1.1.1",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "cloudflare-dot",
        "name": "Cloudflare (DoT)",
        "regions": ["US"],
        "target": "one.one.one.one",
        "transport": "DoT",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "cloudflare-doh",
        "name": "Cloudflare (DoH)",
        "regions": ["US"],
        "target": "https://cloudflare-dns.com/dns-query",
        "transport": "DoH",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-noads-do53",
        "name": "DNS4EU (Protective + Ad Blocking, Do53)",
        "regions": ["EU", "CZ"],
        "target": "86.54.11.13",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-noads-dot",
        "name": "DNS4EU (Protective + Ad Blocking, DoT)",
        "regions": ["EU", "CZ"],
        "target": "noads.joindns4.eu",
        "transport": "DoT",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-noads-doh",
        "name": "DNS4EU (Protective + Ad Blocking, DoH)",
        "regions": ["EU", "CZ"],
        "target": "https://noads.joindns4.eu/dns-query",
        "transport": "DoH",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "quad9-default",
        "name": "Quad9 (malware blocking by default)",
        "regions": ["EU", "CH"],
        "target": "9.9.9.9",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "nextdns-default",
        "name": "NextDNS",
        "regions": ["US"],
        "target": "45.90.28.0",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "adguard-filtered",
        "name": "AdGuard (default filtering)",
        "regions": ["EU", "CY"],
        "target": "94.140.14.14",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "controld-filtered",
        "name": "ControlD (no-ads-gambling-malware-typo)",
        "regions": ["CA"],
        "target": "76.76.2.11",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "mullvad-base-dot",
        "name": "mullvad (base ads,malware)",
        "regions": ["EU", "SE"],
        "target": "194.242.2.4",
        "transport": "DoT",
        "tls_hostname": "base.dns.mullvad.net",
        "doh_method": "POST",
    },
    {
        "id": "mullvad-adblock-dot",
        "name": "mullvad (ads)",
        "regions": ["EU", "SE"],
        "target": "194.242.2.3",
        "transport": "DoT",
        "tls_hostname": "adblock.dns.mullvad.net",
        "doh_method": "POST",
    },
    {
        "id": "mullvad-default-dot",
        "name": "mullvad",
        "regions": ["EU", "SE"],
        "target": "194.242.2.2",
        "transport": "DoT",
        "tls_hostname": "dns.mullvad.net",
        "doh_method": "POST",
    },
    {
        "id": "gcore-default",
        "name": "Gcore",
        "regions": ["EU", "LU"],
        "target": "95.85.95.85",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "flashstart-default",
        "name": "FlashStart",
        "regions": ["EU", "IT"],
        "target": "185.236.104.104",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "google-default",
        "name": "Google",
        "regions": ["US"],
        "target": "8.8.8.8",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-default",
        "name": "DNS4EU",
        "regions": ["EU", "CZ"],
        "target": "86.54.11.100",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "adguard-default",
        "name": "AdGuard",
        "regions": ["EU", "CY"],
        "target": "94.140.14.140",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
]
