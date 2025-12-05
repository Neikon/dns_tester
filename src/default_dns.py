# default_dns.py
#
# Default DNS entries shipped with the application.
# Keep values in English and only include IPs that work out of the box.

DEFAULT_DNS: list[tuple[str, str]] = [
    ("Google DNS", "8.8.8.8"),
    ("Cloudflare DNS (unfiltered)", "1.1.1.1"),
    # ("Cloudflare DNS (malware blocking)", "1.1.1.2"),
    # ("Cloudflare DNS (family filtering)", "1.1.1.3"),
    # ("Quad9 DNS (malware blocking)", "9.9.9.9"),
    # ("Quad9 DNS (unfiltered)", "9.9.9.10"),
    # ("NextDNS", "45.90.28.0"),
    # ("DNS4EU (standard primary)", "193.110.81.0"),
    # ("DNS4EU (standard secondary)", "185.253.5.0"),
    # ("DNS4EU (filtering primary)", "193.110.81.9"),
    # ("DNS4EU (filtering secondary)", "185.253.5.9"),
    # ("AdGuard DNS (non-filtering)", "94.140.14.140"),
    # ("AdGuard DNS (default filtering)", "94.140.14.14"),
    # ("AdGuard DNS (family filtering)", "94.140.14.15"),
]
