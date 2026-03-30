# default_dns.py
#
# Default DNS entries shipped with the application.
# Keep values in English and only include resolvers that work out of the box.

from __future__ import annotations

from typing import TypedDict


class DefaultDnsEntry(TypedDict):
    """Structure used by the bundled DNS catalog."""

    id: str
    provider_name: str
    profile_name: str
    regions: list[str]
    target: str
    transport: str
    tls_hostname: str | None
    doh_method: str


# Bundled resolver entries use stable IDs so users can hide a default entry permanently.
DEFAULT_DNS: list[DefaultDnsEntry] = [
    {
        "id": "cloudflare-do53",
        "provider_name": "Cloudflare",
        "profile_name": "Default",
        "regions": ["US"],
        "target": "1.1.1.1",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "cloudflare-dot",
        "provider_name": "Cloudflare",
        "profile_name": "Default",
        "regions": ["US"],
        "target": "one.one.one.one",
        "transport": "DoT",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "cloudflare-doh",
        "provider_name": "Cloudflare",
        "profile_name": "Default",
        "regions": ["US"],
        "target": "https://cloudflare-dns.com/dns-query",
        "transport": "DoH",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-noads-do53",
        "provider_name": "DNS4EU",
        "profile_name": "Protective + Ad Blocking",
        "regions": ["EU", "CZ"],
        "target": "86.54.11.13",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-noads-dot",
        "provider_name": "DNS4EU",
        "profile_name": "Protective + Ad Blocking",
        "regions": ["EU", "CZ"],
        "target": "noads.joindns4.eu",
        "transport": "DoT",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-noads-doh",
        "provider_name": "DNS4EU",
        "profile_name": "Protective + Ad Blocking",
        "regions": ["EU", "CZ"],
        "target": "https://noads.joindns4.eu/dns-query",
        "transport": "DoH",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "quad9-default",
        "provider_name": "Quad9",
        "profile_name": "Malware Blocking",
        "regions": ["EU", "CH"],
        "target": "9.9.9.9",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "nextdns-default",
        "provider_name": "NextDNS",
        "profile_name": "Default",
        "regions": ["US"],
        "target": "45.90.28.0",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "adguard-filtered",
        "provider_name": "AdGuard",
        "profile_name": "Default Filtering",
        "regions": ["EU", "CY"],
        "target": "94.140.14.14",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "controld-filtered",
        "provider_name": "ControlD",
        "profile_name": "No Ads + Gambling + Malware + Typo",
        "regions": ["CA"],
        "target": "76.76.2.11",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "mullvad-base-dot",
        "provider_name": "Mullvad",
        "profile_name": "Base Ads + Malware",
        "regions": ["EU", "SE"],
        "target": "194.242.2.4",
        "transport": "DoT",
        "tls_hostname": "base.dns.mullvad.net",
        "doh_method": "POST",
    },
    {
        "id": "mullvad-adblock-dot",
        "provider_name": "Mullvad",
        "profile_name": "Ad Blocking",
        "regions": ["EU", "SE"],
        "target": "194.242.2.3",
        "transport": "DoT",
        "tls_hostname": "adblock.dns.mullvad.net",
        "doh_method": "POST",
    },
    {
        "id": "mullvad-default-dot",
        "provider_name": "Mullvad",
        "profile_name": "Default",
        "regions": ["EU", "SE"],
        "target": "194.242.2.2",
        "transport": "DoT",
        "tls_hostname": "dns.mullvad.net",
        "doh_method": "POST",
    },
    {
        "id": "gcore-default",
        "provider_name": "Gcore",
        "profile_name": "Default",
        "regions": ["EU", "LU"],
        "target": "95.85.95.85",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "flashstart-default",
        "provider_name": "FlashStart",
        "profile_name": "Default",
        "regions": ["EU", "IT"],
        "target": "185.236.104.104",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "google-default",
        "provider_name": "Google",
        "profile_name": "Default",
        "regions": ["US"],
        "target": "8.8.8.8",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-default",
        "provider_name": "DNS4EU",
        "profile_name": "Default",
        "regions": ["EU", "CZ"],
        "target": "86.54.11.100",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "adguard-default",
        "provider_name": "AdGuard",
        "profile_name": "Default",
        "regions": ["EU", "CY"],
        "target": "94.140.14.140",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
]
