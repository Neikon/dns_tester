# default_dns.py
#
# Default DNS entries shipped with the application.
# Keep values in English and only include resolvers that work out of the box.

# Bundled resolver entries store the label, endpoint, transport, and optional TLS/bootstrap hint.
DEFAULT_DNS: list[tuple[str, str, str, str | None]] = [
    ("🇪🇺DNS4EU (Protective + Ad Blocking, DoH)", "https://noads.joindns4.eu/dns-query", "DoH", None),
    ("🇪🇺DNS4EU (Protective + Ad Blocking, DoT)", "noads.joindns4.eu", "DoT", None),
    ("🇪🇺DNS4EU (Protective + Ad Blocking)", "86.54.11.13", "Do53", None),
    ("🇪🇺Quad9 (malware blocking by default)", "9.9.9.9", "Do53", None),
    ("🇺🇸NextDNS", "45.90.28.0", "Do53", None),
    ("🇷🇺/🇪🇺 AdGuard (default filtering)", "94.140.14.14", "Do53", None),
    ("🇨🇦ControlD (no-ads-gambling-malware-typo)", "76.76.2.11", "Do53", None),
    ("🇪🇺mullvad (base ads,malware)", "194.242.2.4", "DoT", "base.dns.mullvad.net"),
    ("🇪🇺mullvad (ads)", "194.242.2.3", "DoT", "adblock.dns.mullvad.net"),
    ("🇪🇺mullvad", "194.242.2.2", "DoT", "dns.mullvad.net"),
    ("🇪🇺Gcore", "95.85.95.85", "Do53", None),
    ("🇪🇺FlashStart", "185.236.104.104", "Do53", None),
    ("🇺🇸Cloudflare (malware blocking)", "1.1.1.2", "Do53", None),
    ("🇺🇸Google", "8.8.8.8", "Do53", None),
    ("🇺🇸Cloudflare", "1.1.1.1", "Do53", None),
    ("🇪🇺DNS4EU", "86.54.11.100", "Do53", None),
    ("🇷🇺/🇪🇺 AdGuard", "94.140.14.140", "Do53", None),
]
