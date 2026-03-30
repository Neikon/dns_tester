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
    target: str
    transport: str
    tls_hostname: str | None
    doh_method: str


# Bundled resolver entries use stable IDs so users can hide a default entry permanently.
DEFAULT_DNS: list[DefaultDnsEntry] = [
    {
        "id": "cloudflare-do53",
        "name": "🇺🇸Cloudflare (Do53)",
        "target": "1.1.1.1",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "cloudflare-dot",
        "name": "🇺🇸Cloudflare (DoT)",
        "target": "one.one.one.one",
        "transport": "DoT",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "cloudflare-doh",
        "name": "🇺🇸Cloudflare (DoH)",
        "target": "https://cloudflare-dns.com/dns-query",
        "transport": "DoH",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-noads-do53",
        "name": "🇪🇺DNS4EU (Protective + Ad Blocking, Do53)",
        "target": "86.54.11.13",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-noads-dot",
        "name": "🇪🇺DNS4EU (Protective + Ad Blocking, DoT)",
        "target": "noads.joindns4.eu",
        "transport": "DoT",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-noads-doh",
        "name": "🇪🇺DNS4EU (Protective + Ad Blocking, DoH)",
        "target": "https://noads.joindns4.eu/dns-query",
        "transport": "DoH",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "quad9-default",
        "name": "🇪🇺Quad9 (malware blocking by default)",
        "target": "9.9.9.9",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "nextdns-default",
        "name": "🇺🇸NextDNS",
        "target": "45.90.28.0",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "adguard-filtered",
        "name": "🇷🇺/🇪🇺 AdGuard (default filtering)",
        "target": "94.140.14.14",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "controld-filtered",
        "name": "🇨🇦ControlD (no-ads-gambling-malware-typo)",
        "target": "76.76.2.11",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "mullvad-base-dot",
        "name": "🇪🇺mullvad (base ads,malware)",
        "target": "194.242.2.4",
        "transport": "DoT",
        "tls_hostname": "base.dns.mullvad.net",
        "doh_method": "POST",
    },
    {
        "id": "mullvad-adblock-dot",
        "name": "🇪🇺mullvad (ads)",
        "target": "194.242.2.3",
        "transport": "DoT",
        "tls_hostname": "adblock.dns.mullvad.net",
        "doh_method": "POST",
    },
    {
        "id": "mullvad-default-dot",
        "name": "🇪🇺mullvad",
        "target": "194.242.2.2",
        "transport": "DoT",
        "tls_hostname": "dns.mullvad.net",
        "doh_method": "POST",
    },
    {
        "id": "gcore-default",
        "name": "🇪🇺Gcore",
        "target": "95.85.95.85",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "flashstart-default",
        "name": "🇪🇺FlashStart",
        "target": "185.236.104.104",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "google-default",
        "name": "🇺🇸Google",
        "target": "8.8.8.8",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "dns4eu-default",
        "name": "🇪🇺DNS4EU",
        "target": "86.54.11.100",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
    {
        "id": "adguard-default",
        "name": "🇷🇺/🇪🇺 AdGuard",
        "target": "94.140.14.140",
        "transport": "Do53",
        "tls_hostname": None,
        "doh_method": "POST",
    },
]
