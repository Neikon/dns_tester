# default_dns.py
#
# Default DNS entries shipped with the application.
# Keep values in English and only include IPs that work out of the box.

DEFAULT_DNS: list[tuple[str, str]] = [
    ("Google", "8.8.8.8"),
    ("Cloudflare (unfiltered)", "1.1.1.1"),
    ("Cloudflare (malware blocking)", "1.1.1.2"),
    ("Cloudflare (family filtering)", "1.1.1.3"),
    ("Quad9 (malware blocking by default)", "9.9.9.9"),
    ("NextDNS", "45.90.28.0"),
    ("DNS4EU", "86.54.11.100"),
    ("DNS4EU (Protective)", "86.54.11.1"),
    ("DNS4EU (Protective + Ad Blocking)", "86.54.11.13"),
    ("AdGuard", "94.140.14.140"),
    ("AdGuard (default filtering)", "94.140.14.14"),
]
