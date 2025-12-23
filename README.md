# DNS Tester

DNS Tester is a GTK4/Libadwaita desktop app to compare public DNS resolvers and measure their responsiveness using a real-world workload: the 50 most visited websites in Spain.

## Features
- Preloaded resolvers (removable/customizable): [src/default_dns.py](https://github.com/Neikon/dns_tester/blob/main/src/default_dns.py) (Google, Cloudflare, Quad9, DNS4EU, AdGuard, and more).
- Inline testing: each DNS entry has a play button to run a latency test; results appear immediately in the row.
- Bulk test: “Check All” runs tests for every DNS in parallel (threaded) and updates rows as results arrive.
- Basic IP validation when adding custom DNS servers (IPv4/IPv6).

## How latency is measured
For each resolver, the app resolves the 50 top Spanish websites (see `src/aux.py`). It records the round-trip time reported by dnspython for each query and summarizes per resolver: average, best, worst, and error count.

## Download, install, and use (Flatpak)
1. Download the latest `.flatpak` bundle from the releases page: https://github.com/Neikon/dns_tester/releases
2. Install the bundle (or open it with your software center):
```bash
# Replace the filename with the one you downloaded
flatpak install --user ./dns_tester.flatpak
```
3. Launch the app from your desktop menu, or run:
```bash
# Launch DNS Tester
flatpak run es.neikon.dns_tester
```

## Notes
- UI built with Libadwaita (GTK 4).
- License: GPL-3.0-or-later.
- Repository & issues: https://github.com/Neikon/dns_tester

## Roadmap
- [ ] Sort servers automatically by their measured latency so the fastest resolvers appear first.
- [ ] Persist custom DNS entries across sessions.
- [ ] Export/import resolver lists.
