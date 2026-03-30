# default_dns.py
#
# Default DNS entries shipped with the application.
# Keep values in English and only include IPs that work out of the box.

DEFAULT_DNS: list[tuple[str, str]] = [
    ("🇪🇺DNS4EU (Protective + Ad Blocking)", "86.54.11.13"),
    ("🇪🇺Quad9 (malware blocking by default)", "9.9.9.9"),
    ("🇺🇸NextDNS", "45.90.28.0"),
    ("🇷🇺/🇪🇺 AdGuard (default filtering)", "94.140.14.14"),
    ("🇨🇦ControlD (no-ads-gambling-malware-typo)", "76.76.2.11"),
    ("🇪🇺mullvad (base ads,malware)", "194.242.2.4"),
    ("🇪🇺mullvad (ads)", "194.242.2.3"),
    ("🇪🇺mullvad", "194.242.2.2"),
    ("🇪🇺Gcore", "95.85.95.85"),
    ("🇪🇺FlashStart", "185.236.104.104"),
    ("🇺🇸Cloudflare (malware blocking)", "1.1.1.2"),
    ("🇺🇸Google", "8.8.8.8"),
    ("🇺🇸Cloudflare", "1.1.1.1"),
    ("🇪🇺DNS4EU", "86.54.11.100"),
    ("🇷🇺/🇪🇺 AdGuard", "94.140.14.140"),
]
