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

import threading

import dns.resolver
from gi.repository import GLib
from .aux import TOP_ES_WEBS
from .default_dns import DEFAULT_DNS
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
        # Default domain and record type used for DNS queries.
        self.test_domain = "example.com"
        self.test_record_type = "A"

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

        # Add sample rows for DNS entries from the bundled defaults.
        for name, ip in DEFAULT_DNS:
            self._add_row(name, ip)

        # Insert the list box into the main container.
        self.content_box.append(self.list_box)

    def _add_row(self, name: str, ip_address: str) -> None:
        """Create and append an expander row with the given name and IP."""
        expander_row = Adw.ExpanderRow(
            title=name,
            subtitle=ip_address,
            activatable=False,
            selectable=False,
        )
        remove_button = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        remove_button.add_css_class("destructive-action")
        remove_button.add_css_class("flat")
        remove_button.set_tooltip_text("Remove entry")
        remove_button.connect(
            "clicked",
            lambda _btn: self.list_box.remove(expander_row),
        )
        # Nested action row to display results or extra info.
        result_row = Adw.ActionRow(
            title="Results pending",
            subtitle="",
            activatable=False,
            selectable=False,
        )
        expander_row.result_row = result_row
        test_button = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        test_button.add_css_class("flat")
        test_button.set_tooltip_text("Test this DNS")

        test_button.connect("clicked", self._run_test_async, expander_row, result_row)
        result_row.add_suffix(test_button)
        expander_row.add_row(result_row)

        expander_row.add_suffix(remove_button)
        self.list_box.append(expander_row)
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
        """Run individual checks sequentially and update each row inline."""
        row = self.list_box.get_first_child()
        print("[DNS check] Running all rows...")
        while row is not None:
            if isinstance(row, Adw.ExpanderRow):
                result_row = getattr(row, "result_row", None)
                if isinstance(result_row, Adw.ActionRow):
                    self._run_test_async(None, row, result_row)
            row = row.get_next_sibling()

    def _resolve_dns(self, ip_address: str) -> str:
        """Resolve many domains via the given DNS server and report latency stats."""
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [ip_address]
        resolver.lifetime = 2.0

        latencies: list[float] = []
        errors = 0

        for domain in TOP_ES_WEBS:
            try:
                answer = resolver.resolve(
                    domain,
                    self.test_record_type,
                    lifetime=resolver.lifetime,
                )
                latency_ms = (answer.response.time or 0) * 1000.0
                latencies.append(latency_ms)
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout):
                errors += 1
            except Exception:
                errors += 1

        if not latencies:
            return "no successful responses"

        best = min(latencies)
        worst = max(latencies)
        avg = sum(latencies) / len(latencies)
        summary = f"avg {avg:.1f} ms | best {best:.1f} ms | worst {worst:.1f} ms"
        if errors:
            summary += f" | errors {errors}"
        return summary

    def _run_test_async(self, _btn: Gtk.Button | None, expander_row: Adw.ExpanderRow, result_row: Adw.ActionRow) -> None:
        """Resolve only this DNS in a worker thread and update its nested result row."""
        ip = expander_row.get_subtitle() or ""
        if not ip:
            result_row.set_title("No IP set")
            result_row.set_subtitle("")
            return

        result_row.set_title("Testing...")
        result_row.set_subtitle("Working...")
        expander_row.set_expanded(True)
        self.list_box.queue_draw()

        def worker() -> None:
            result = self._resolve_dns(ip)

            def update_ui() -> bool:
                result_row.set_title("Result")
                result_row.set_subtitle(result)
                result_row.add_css_class("property")
                expander_row.set_expanded(True)
                result_row.queue_draw()
                expander_row.queue_draw()
                self.list_box.queue_draw()
                return False

            GLib.idle_add(update_ui)

        threading.Thread(target=worker, daemon=True).start()
