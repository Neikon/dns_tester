# dns_groups.py
#
# Group DNS entries by provider and profile so the UI can present one card per
# logical DNS offering instead of one row per transport endpoint.

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from .dns_store import DnsEntry
from .region_info import decorate_name_with_regions

# Transport order stays stable so grouped variants always appear predictably.
TRANSPORT_ORDER = {
    "Do53": 0,
    "DoT": 1,
    "DoH": 2,
}


@dataclass
class DnsProfileGroup:
    """Collection of DNS variants that belong to one provider/profile pair."""

    provider_name: str
    profile_name: str
    regions: list[str]
    entries: list[DnsEntry] = field(default_factory=list)


def _merge_regions(existing_regions: list[str], new_regions: list[str]) -> list[str]:
    """Merge region labels while preserving the first-seen order."""
    merged_regions = list(existing_regions)
    for region in new_regions:
        if region not in merged_regions:
            merged_regions.append(region)
    return merged_regions


def group_dns_entries(entries: list[DnsEntry]) -> list[DnsProfileGroup]:
    """Group DNS entries by provider/profile while keeping catalog order intact."""
    grouped_entries: dict[tuple[str, str], DnsProfileGroup] = {}
    ordered_groups: list[DnsProfileGroup] = []

    for entry in entries:
        group_key = (entry.provider_name, entry.profile_name)
        group = grouped_entries.get(group_key)
        if group is None:
            group = DnsProfileGroup(
                provider_name=entry.provider_name,
                profile_name=entry.profile_name,
                regions=list(entry.regions),
            )
            grouped_entries[group_key] = group
            ordered_groups.append(group)
        else:
            group.regions = _merge_regions(group.regions, entry.regions)
        group.entries.append(entry)

    for group in ordered_groups:
        group.entries.sort(key=lambda entry: TRANSPORT_ORDER.get(entry.transport, 99))

    return ordered_groups


def group_display_name(group: DnsProfileGroup) -> str:
    """Build the top-level group title decorated with region flags."""
    return decorate_name_with_regions(group.provider_name, group.regions)


def group_transport_summary(group: DnsProfileGroup) -> str:
    """Render a compact transport list for the group subtitle."""
    transports = [entry.transport for entry in group.entries]
    return " · ".join(transports)


def variant_display_name(entry: DnsEntry) -> str:
    """Render the fully qualified variant label used in rankings and logs."""
    return f"{entry.provider_name} / {entry.profile_name} / {entry.transport}"
