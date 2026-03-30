# appdata.py
#
# Helpers for reading release metadata from the AppStream file.
# This keeps the About dialog in sync with the packaged metainfo file.

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

from gi.repository import GLib

# The metainfo filename is fixed by the application ID.
APPDATA_FILENAME = "es.neikon.dns_tester.metainfo.xml"


def _appdata_candidates() -> list[str]:
    """Return possible filesystem locations for the AppStream metainfo file."""
    source_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return [
        os.path.join(source_root, "data", f"{APPDATA_FILENAME}.in"),
        os.path.join(source_root, "data", APPDATA_FILENAME),
        os.path.join(GLib.get_user_data_dir(), "metainfo", APPDATA_FILENAME),
        *[
            os.path.join(data_dir, "metainfo", APPDATA_FILENAME)
            for data_dir in GLib.get_system_data_dirs()
        ],
    ]


def _find_appdata_path() -> str | None:
    """Return the first existing metainfo path."""
    for candidate in _appdata_candidates():
        if os.path.exists(candidate):
            return candidate
    return None


def load_latest_release_notes() -> tuple[str | None, str | None]:
    """Read the newest release version and release notes from the AppStream file."""
    appdata_path = _find_appdata_path()
    if appdata_path is None:
        return None, None

    try:
        tree = ET.parse(appdata_path)
    except (ET.ParseError, OSError):
        return None, None

    release_element = tree.find("./releases/release")
    if release_element is None:
        return None, None

    version = release_element.get("version")
    description_element = release_element.find("description")
    if description_element is None:
        return version, None

    # Libadwaita expects the inner release-notes markup, not the wrapping
    # <description> element from AppStream metadata.
    release_notes = "".join(
        ET.tostring(child, encoding="unicode", method="xml")
        for child in description_element
    ).strip()
    if not release_notes:
        return version, None
    return version, release_notes
