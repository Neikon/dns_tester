# DNS Tester

DNS Tester is a GTK4/Libadwaita desktop app to compare public DNS resolvers and measure their responsiveness using a real-world workload: the 50 most visited websites in Spain.

## Features
- Preloaded resolvers: Google, Cloudflare (unfiltered/malware/family), Quad9, DNS4EU variants, AdGuard variants, and you can add your own.
- Inline testing: each DNS entry has a play button to run a latency test; results appear immediately in the row.
- Bulk test: “Check All” runs tests for every DNS in parallel (threaded) and updates rows as results arrive.
- Basic IP validation when adding custom DNS servers (IPv4/IPv6).
- Removable rows and default list stored in `src/default_dns.py`.

## How latency is measured
For each resolver, the app resolves the 50 top Spanish websites (see `src/aux.py`). It records the round-trip time reported by dnspython for each query and summarizes per resolver: average, best, worst, and error count.

## Running
```bash
meson setup builddir
meson compile -C builddir
./builddir/dns_tester
```

## Notes
- UI built with Libadwaita (GTK 4).
- License: GPL-3.0-or-later.
- Repository & issues: https://github.com/Neikon/dns_tester
