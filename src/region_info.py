# region_info.py
#
# Structured region metadata used by DNS entries.
# Keeping it outside the window module avoids mixing UI code with static catalogs.

from __future__ import annotations

# Region labels stay centralized so catalogs and UI formatting use the same vocabulary.
REGION_LABELS = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DK": "Denmark",
    "EU": "Europe",
    "EE": "Estonia",
    "FI": "Finland",
    "FR": "France",
    "DE": "Germany",
    "GR": "Greece",
    "HU": "Hungary",
    "IE": "Ireland",
    "IT": "Italy",
    "LV": "Latvia",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MT": "Malta",
    "NL": "Netherlands",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "ES": "Spain",
    "SE": "Sweden",
    "CH": "Switzerland",
    "US": "United States",
    "RU": "Russia",
    "CA": "Canada",
    "CN": "China",
    "JP": "Japan",
}

# Flags are stored separately so callers can render labels with or without emoji.
REGION_FLAGS = {
    "AT": "🇦🇹",
    "BE": "🇧🇪",
    "BG": "🇧🇬",
    "HR": "🇭🇷",
    "CY": "🇨🇾",
    "CZ": "🇨🇿",
    "DK": "🇩🇰",
    "EU": "🇪🇺",
    "EE": "🇪🇪",
    "FI": "🇫🇮",
    "FR": "🇫🇷",
    "DE": "🇩🇪",
    "GR": "🇬🇷",
    "HU": "🇭🇺",
    "IE": "🇮🇪",
    "IT": "🇮🇹",
    "LV": "🇱🇻",
    "LT": "🇱🇹",
    "LU": "🇱🇺",
    "MT": "🇲🇹",
    "NL": "🇳🇱",
    "PL": "🇵🇱",
    "PT": "🇵🇹",
    "RO": "🇷🇴",
    "SK": "🇸🇰",
    "SI": "🇸🇮",
    "ES": "🇪🇸",
    "SE": "🇸🇪",
    "CH": "🇨🇭",
    "US": "🇺🇸",
    "RU": "🇷🇺",
    "CA": "🇨🇦",
    "CN": "🇨🇳",
    "JP": "🇯🇵",
}


def format_region_summary(regions: list[str]) -> str:
    """Render a readable region string with flags and labels."""
    region_parts = []
    for region in regions:
        label = REGION_LABELS.get(region, region)
        flag = REGION_FLAGS.get(region)
        region_parts.append(f"{flag} {label}" if flag else label)
    return ", ".join(region_parts)


def decorate_name_with_regions(name: str, regions: list[str]) -> str:
    """Render a display title from the clean provider name plus region flags."""
    flags = " ".join(REGION_FLAGS[region] for region in regions if region in REGION_FLAGS)
    return f"{flags} {name}".strip() if flags else name
