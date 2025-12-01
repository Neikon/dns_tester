# window.py
#
# Copyright 2025 neikon
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import re
import subprocess

from gi.repository import Adw
from gi.repository import Gtk

@Gtk.Template(resource_path='/es/neikon/dns_tester/window.ui')
class DnsTesterWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'DnsTesterWindow'

    # Button in the header to trigger row creation.
    add_button = Gtk.Template.Child()
    # Main container from the template where we add dynamic widgets.
    content_box = Gtk.Template.Child()
    # Bottom button to run DNS latency checks.
    check_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Counter keeps track of how many rows exist for incremental labels.
        self.entry_count = 0

        # Build the list box dynamically so the UI file stays minimal.
        self.list_box = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            hexpand=True,
            vexpand=True,
            css_classes=['boxed-list-separate'],
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )

        # Add sample rows for DNS entries; will be replaced with real data later.
        self._add_row("Primary DNS", "8.8.8.8")
        self._add_row("Secondary DNS", "1.1.1.1")

        # Insert the list box into the main container.
        self.content_box.append(self.list_box)

    def _add_row(self, name: str, ip_address: str) -> None:
        """Create and append an action row with the given name and IP."""
        action_row = Adw.ActionRow(
            title=name,
            subtitle=ip_address,
            activatable=False,
            selectable=False,
        )
        self.list_box.append(action_row)
        self.entry_count += 1

    def _show_add_dialog(self) -> None:
        """Show an Adwaita dialog asking for name and IP, then append a row on confirm."""
        dialog = Adw.Dialog.new()
        dialog.set_title("Add DNS Entry")
        dialog.set_content_width(360)
        dialog.set_content_height(220)
        dialog.set_can_close(True)

        content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        name_row = Adw.EntryRow(title="Name")
        ip_row = Adw.EntryRow(title="IP Address")
        content_box.append(name_row)
        content_box.append(ip_row)

        # Action buttons to cancel or confirm the dialog; stretched to share full width.
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, hexpand=True)
        button_box.set_homogeneous(True)
        cancel_btn = Gtk.Button(label="_Cancel", use_underline=True, hexpand=True)
        add_btn = Gtk.Button(label="_Add", use_underline=True, hexpand=True)
        add_btn.add_css_class("suggested-action")
        button_box.append(cancel_btn)
        button_box.append(add_btn)
        content_box.append(button_box)
        dialog.set_child(self._wrap_dialog_content(content_box, "Add DNS Entry"))

        def close_dialog(_button: Gtk.Button) -> None:
            """Close the dialog without adding a row."""
            dialog.close()

        def confirm_dialog(_button: Gtk.Button | None = None) -> None:
            """Add the row if data is present and close the dialog."""
            name = name_row.get_text().strip()
            ip_address = ip_row.get_text().strip()
            if name and ip_address:
                self._add_row(name, ip_address)
                dialog.close()

        cancel_btn.connect("clicked", close_dialog)
        add_btn.connect("clicked", confirm_dialog)
        name_row.connect("activate", confirm_dialog)
        ip_row.connect("activate", confirm_dialog)
        dialog.set_default_widget(add_btn)
        dialog.present(self)

    @Gtk.Template.Callback()
    def on_add_button_clicked(self, _button: Gtk.Button) -> None:
        """Open a dialog to capture name and IP, then append a new entry row."""
        self._show_add_dialog()

    @Gtk.Template.Callback()
    def on_check_button_clicked(self, _button: Gtk.Button) -> None:
        """Ping every DNS entry and show latencies inside an Adwaita dialog."""
        results: list[tuple[str, str]] = []
        dialog, results_box = self._create_results_dialog(title="Testing")
        dialog.present(self)

        row = self.list_box.get_first_child()
        while row is not None:
            # ListBox wraps children, so unwrap if needed.
            entry_widget = row.get_child() if isinstance(row, Gtk.ListBoxRow) else row
            if isinstance(entry_widget, Adw.ActionRow):
                name = entry_widget.get_title() or "Unknown"
                ip_address = entry_widget.get_subtitle() or ""
                latency = self._ping_ip(ip_address) if ip_address else "missing IP"
                results.append((name, latency))
            row = row.get_next_sibling()

        # Populate the dialog list with results.
        self._populate_results_list(results_box, results)
        dialog.set_title("Results")

    def _ping_ip(self, ip_address: str) -> str:
        """Run a single ping and return the latency text or an error note."""
        cmd = ["ping", "-c", "1", "-W", "1", ip_address]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001
            return f"error: {exc}"

        if completed.returncode != 0:
            return "timeout/unreachable"

        match = re.search(r"time=([0-9.]+)\\s*ms", completed.stdout)
        if match:
            return f"{match.group(1)} ms"
        return "latency unavailable"

    def _create_results_dialog(self, title: str) -> tuple[Adw.Dialog, Gtk.ListBox]:
        """Create an Adwaita dialog prepared to display ping results."""
        dialog = Adw.Dialog.new()
        dialog.set_title(title)
        dialog.set_content_width(420)
        dialog.set_content_height(280)
        dialog.set_can_close(True)

        content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )

        results_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        results_box.add_css_class("boxed-list-separate")
        content_box.append(results_box)

        dialog.set_child(self._wrap_dialog_content(content_box, title))
        return dialog, results_box

    def _populate_results_list(self, results_box: Gtk.ListBox, results: list[tuple[str, str]]) -> None:
        """Fill the given list box with latency results."""
        for name, latency in results:
            row = Adw.ActionRow(title=name, subtitle=latency, activatable=False, selectable=False)
            results_box.append(row)

    def _wrap_dialog_content(self, body: Gtk.Widget, title: str) -> Adw.ToolbarView:
        """Wrap dialog content in a toolbar view with a header bar for a clean title/close layout."""
        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(Gtk.Label(label=title))
        header_bar.set_show_start_title_buttons(False)
        header_bar.set_show_end_title_buttons(True)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        toolbar_view.set_content(body)
        return toolbar_view
