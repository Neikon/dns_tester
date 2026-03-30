# dns_store.py
#
# Persist DNS entries chosen by the user.
# The bundled catalog stays in Python code, while user state is stored as JSON.

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass

from gi.repository import GLib

from .default_dns import DefaultDnsEntry

# Persisted data is versioned so the schema can evolve without guessing.
STATE_VERSION = 2


@dataclass(frozen=True)
class DnsEntry:
    """Full DNS entry used by the window layer."""

    id: str
    provider_name: str
    profile_name: str
    regions: list[str]
    target: str
    transport: str
    tls_hostname: str | None
    doh_method: str
    is_default: bool


class DnsStateStore:
    """Load and save hidden default entries and custom user entries."""

    def __init__(self) -> None:
        config_dir = os.path.join(GLib.get_user_config_dir(), "es.neikon.dns_tester")
        self.state_path = os.path.join(config_dir, "dns_servers.json")

    def _default_state(self) -> dict[str, object]:
        """Return the empty persisted state."""
        return {
            "version": STATE_VERSION,
            "hidden_default_ids": [],
            "custom_entries": [],
        }

    def _normalize_custom_entry(self, entry: object) -> dict[str, object] | None:
        """Validate one persisted custom entry and discard malformed data."""
        if not isinstance(entry, dict):
            return None

        provider_name = entry.get("provider_name")
        if not isinstance(provider_name, str) or not provider_name:
            legacy_name = entry.get("name")
            if isinstance(legacy_name, str) and legacy_name:
                provider_name = legacy_name
            else:
                provider_name = None

        profile_name = entry.get("profile_name")
        if not isinstance(profile_name, str) or not profile_name:
            profile_name = "Custom"

        normalized = {
            "id": entry.get("id"),
            "provider_name": provider_name,
            "profile_name": profile_name,
            "regions": entry.get("regions", []),
            "target": entry.get("target"),
            "transport": entry.get("transport"),
            "tls_hostname": entry.get("tls_hostname"),
            "doh_method": entry.get("doh_method", "POST"),
        }
        required_fields = ("id", "provider_name", "profile_name", "target", "transport", "doh_method")
        if not all(isinstance(normalized[field], str) and normalized[field] for field in required_fields):
            return None
        if not isinstance(normalized["regions"], list):
            normalized["regions"] = []
        normalized["regions"] = [
            region for region in normalized["regions"] if isinstance(region, str) and region
        ]
        if normalized["tls_hostname"] is not None and not isinstance(normalized["tls_hostname"], str):
            normalized["tls_hostname"] = None
        return normalized

    def _load_state(self) -> dict[str, object]:
        """Read the JSON state from disk and fall back to an empty state on errors."""
        if not os.path.exists(self.state_path):
            return self._default_state()

        try:
            with open(self.state_path, encoding="utf-8") as state_file:
                raw_state = json.load(state_file)
        except (OSError, json.JSONDecodeError):
            return self._default_state()

        if not isinstance(raw_state, dict):
            return self._default_state()

        hidden_default_ids = raw_state.get("hidden_default_ids", [])
        custom_entries = raw_state.get("custom_entries", [])
        if not isinstance(hidden_default_ids, list):
            hidden_default_ids = []
        if not isinstance(custom_entries, list):
            custom_entries = []

        normalized_custom_entries = []
        for entry in custom_entries:
            normalized_entry = self._normalize_custom_entry(entry)
            if normalized_entry is not None:
                normalized_custom_entries.append(normalized_entry)

        return {
            "version": STATE_VERSION,
            "hidden_default_ids": [entry_id for entry_id in hidden_default_ids if isinstance(entry_id, str)],
            "custom_entries": normalized_custom_entries,
        }

    def _save_state(self, state: dict[str, object]) -> None:
        """Write the JSON state atomically so app restarts always see a complete file."""
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        temp_path = f"{self.state_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as state_file:
            json.dump(state, state_file, indent=2, sort_keys=True)
        os.replace(temp_path, self.state_path)

    def load_entries(self, default_entries: list[DefaultDnsEntry]) -> list[DnsEntry]:
        """Combine bundled defaults with persisted user changes."""
        state = self._load_state()
        hidden_default_ids = set(state["hidden_default_ids"])
        entries: list[DnsEntry] = []

        for entry in default_entries:
            if entry["id"] in hidden_default_ids:
                continue
            entries.append(
                DnsEntry(
                    id=entry["id"],
                    provider_name=entry["provider_name"],
                    profile_name=entry["profile_name"],
                    regions=entry["regions"],
                    target=entry["target"],
                    transport=entry["transport"],
                    tls_hostname=entry["tls_hostname"],
                    doh_method=entry["doh_method"],
                    is_default=True,
                )
            )

        for entry in state["custom_entries"]:
            entries.append(
                DnsEntry(
                    id=entry["id"],
                    provider_name=entry["provider_name"],
                    profile_name=entry["profile_name"],
                    regions=entry["regions"],
                    target=entry["target"],
                    transport=entry["transport"],
                    tls_hostname=entry["tls_hostname"],
                    doh_method=entry["doh_method"],
                    is_default=False,
                )
            )

        return entries

    def add_custom_entry(
        self,
        provider_name: str,
        profile_name: str,
        regions: list[str],
        target: str,
        transport: str,
        tls_hostname: str | None,
        doh_method: str,
    ) -> DnsEntry:
        """Persist a new custom DNS entry and return the created record."""
        state = self._load_state()
        entry = {
            "id": f"custom-{uuid.uuid4().hex}",
            "provider_name": provider_name,
            "profile_name": profile_name,
            "regions": regions,
            "target": target,
            "transport": transport,
            "tls_hostname": tls_hostname,
            "doh_method": doh_method,
        }
        state["custom_entries"].append(entry)
        self._save_state(state)
        return DnsEntry(
            id=entry["id"],
            provider_name=provider_name,
            profile_name=profile_name,
            regions=regions,
            target=target,
            transport=transport,
            tls_hostname=tls_hostname,
            doh_method=doh_method,
            is_default=False,
        )

    def hide_default_entry(self, entry_id: str) -> None:
        """Remember that one bundled DNS entry was removed by the user."""
        state = self._load_state()
        hidden_default_ids = set(state["hidden_default_ids"])
        hidden_default_ids.add(entry_id)
        state["hidden_default_ids"] = sorted(hidden_default_ids)
        self._save_state(state)

    def remove_custom_entry(self, entry_id: str) -> None:
        """Delete one custom DNS entry from persisted user state."""
        state = self._load_state()
        state["custom_entries"] = [
            entry for entry in state["custom_entries"] if entry["id"] != entry_id
        ]
        self._save_state(state)

    def reset_hidden_defaults(self) -> None:
        """Restore all bundled DNS entries that were previously hidden by the user."""
        state = self._load_state()
        state["hidden_default_ids"] = []
        self._save_state(state)
