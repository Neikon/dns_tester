# default_dns.py
#
# Default DNS entries shipped with the application.
# Keep values in English and only include resolvers that work out of the box.

# Bundled resolver entries store the label, endpoint, transport, TLS hostname, and DoH method.
DEFAULT_DNS: list[tuple[str, str, str, str | None, str]] = [
    ("🇺🇸Cloudflare (Do53)", "1.1.1.1", "Do53", None, "POST"),
    ("🇺🇸Cloudflare (DoT)", "one.one.one.one", "DoT", None, "POST"),
    ("🇺🇸Cloudflare (DoH)", "https://cloudflare-dns.com/dns-query", "DoH", None, "POST"),
    ("🇪🇺DNS4EU (Protective + Ad Blocking, Do53)", "86.54.11.13", "Do53", None, "POST"),
    ("🇪🇺DNS4EU (Protective + Ad Blocking, DoT)", "noads.joindns4.eu", "DoT", None, "POST"),
    ("🇪🇺DNS4EU (Protective + Ad Blocking, DoH)", "https://noads.joindns4.eu/dns-query", "DoH", None, "POST"),
    ("🇪🇺Quad9 (malware blocking by default)", "9.9.9.9", "Do53", None, "POST"),
    ("🇺🇸NextDNS", "45.90.28.0", "Do53", None, "POST"),
    ("🇷🇺/🇪🇺 AdGuard (default filtering)", "94.140.14.14", "Do53", None, "POST"),
    ("🇨🇦ControlD (no-ads-gambling-malware-typo)", "76.76.2.11", "Do53", None, "POST"),
    ("🇪🇺mullvad (base ads,malware)", "194.242.2.4", "DoT", "base.dns.mullvad.net", "POST"),
    ("🇪🇺mullvad (ads)", "194.242.2.3", "DoT", "adblock.dns.mullvad.net", "POST"),
    ("🇪🇺mullvad", "194.242.2.2", "DoT", "dns.mullvad.net", "POST"),
    ("🇪🇺Gcore", "95.85.95.85", "Do53", None, "POST"),
    ("🇪🇺FlashStart", "185.236.104.104", "Do53", None, "POST"),
    ("🇺🇸Google", "8.8.8.8", "Do53", None, "POST"),
    ("🇪🇺DNS4EU", "86.54.11.100", "Do53", None, "POST"),
    ("🇷🇺/🇪🇺 AdGuard", "94.140.14.140", "Do53", None, "POST"),
]
