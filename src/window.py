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

import ipaddress
import threading
from urllib.parse import urlparse

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from .aux import TOP_ES_WEBS
from .benchmark import BenchmarkResult
from .benchmark import BenchmarkOptions
from .benchmark import ResolverEndpoint
from .benchmark import run_benchmark_sync
from .default_dns import DEFAULT_DNS
from .dns_groups import DnsProfileGroup
from .dns_groups import group_display_name
from .dns_groups import group_dns_entries
from .dns_groups import group_transport_summary
from .dns_groups import variant_display_name
from .dns_store import DnsEntry
from .dns_store import DnsStateStore
from .region_info import format_region_summary

# Supported resolver transports exposed in the add-entry dialog.
TRANSPORTS = ("Do53", "DoT", "DoH")
# DoH RFC 8484 supports both POST and GET, while POST remains the default choice.
DOH_METHODS = ("POST", "GET")


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
        # DNS record type stays configurable internally even if the UI currently defaults to A.
        self.test_record_type = "A"
        # The console table header is printed once per application run for readable logs.
        self._printed_console_header = False
        # Benchmark settings stay in memory and are edited from the preferences dialog.
        self.cache_enabled = False
        self.concurrency_value = 10
        self.warmup_queries_value = 5
        self.preferences_dialog: Adw.Dialog | None = None
        # Batch state tracks a running "Check All" operation and its final ranking.
        self.check_all_batch_id = 0
        self.check_all_pending = 0
        self.check_all_results: list[tuple[str, object]] = []
        # DNS state is persisted separately from the bundled catalog.
        self.dns_store = DnsStateStore()
        self.group_rows: list[Adw.ExpanderRow] = []
        self.variant_rows: list[Adw.ExpanderRow] = []

        # The dynamic resolver list stays below the shared controls.
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

        self.content_box.append(self.list_box)
        self._reload_dns_rows()

    def _reload_dns_rows(self) -> None:
        """Rebuild the visible DNS list from persisted state."""
        row = self.list_box.get_first_child()
        while row is not None:
            next_row = row.get_next_sibling()
            self.list_box.remove(row)
            row = next_row

        self.group_rows = []
        self.variant_rows = []

        for group in group_dns_entries(self.dns_store.load_entries(DEFAULT_DNS)):
            self._add_group_row(group)

    def _reset_default_entries(self) -> None:
        """Restore bundled DNS entries that were previously hidden."""
        try:
            self.dns_store.reset_hidden_defaults()
        except OSError as error:
            self._show_error_dialog("Could not save DNS changes", str(error))
            return
        self._reload_dns_rows()

    def _build_spin_row(
        self,
        title: str,
        subtitle: str,
        value: int,
        lower: int,
        upper: int,
    ) -> tuple[Adw.ActionRow, Gtk.SpinButton]:
        """Create a preferences row with a spin button suffix."""
        row = Adw.ActionRow(
            title=title,
            subtitle=subtitle,
            activatable=False,
            selectable=False,
        )
        spin_button = Gtk.SpinButton.new(
            Gtk.Adjustment(value=value, lower=lower, upper=upper, step_increment=1, page_increment=5),
            1,
            0,
        )
        row.add_suffix(spin_button)
        return row, spin_button

    def _ensure_preferences_dialog(self) -> Adw.Dialog:
        """Build the preferences dialog once and reuse it across openings."""
        if self.preferences_dialog is not None:
            return self.preferences_dialog

        dialog = Adw.Dialog.new()
        dialog.set_title("Preferences")
        dialog.set_content_width(520)
        dialog.set_content_height(460)
        dialog.set_can_close(True)

        toolbar_view = Adw.ToolbarView()
        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        preferences_page = Adw.PreferencesPage(
            title="Benchmark",
            description="Use identical settings across providers to keep transport comparisons fair.",
        )
        benchmark_group = Adw.PreferencesGroup(
            title="Benchmark Settings",
            description="These values apply to all DNS rows and to the Check All action.",
        )

        cache_row = Adw.SwitchRow(
            title="Warm Cache",
            subtitle="Prime a local DNS cache before the measured phase",
            active=self.cache_enabled,
        )
        benchmark_group.add(cache_row)

        concurrency_row, concurrency_spin = self._build_spin_row(
            "Concurrency",
            "Maximum number of workers used during the measured phase",
            self.concurrency_value,
            1,
            50,
        )
        benchmark_group.add(concurrency_row)

        warmup_row, warmup_spin = self._build_spin_row(
            "Warm-up Queries",
            "Number of uncaptured warm-up queries before measuring",
            self.warmup_queries_value,
            0,
            20,
        )
        benchmark_group.add(warmup_row)

        reset_row = Adw.ActionRow(
            title="Reset Defaults",
            subtitle="Restore bundled DNS entries that were removed earlier",
            activatable=False,
            selectable=False,
        )
        reset_button = Gtk.Button(label="Reset")
        reset_button.add_css_class("destructive-action")
        reset_button.connect("clicked", lambda _button: self._reset_default_entries())
        reset_row.add_suffix(reset_button)
        benchmark_group.add(reset_row)

        preferences_page.add(benchmark_group)
        toolbar_view.set_content(preferences_page)
        dialog.set_child(toolbar_view)

        # Widgets are stored on the dialog so values can be read back on every presentation.
        dialog.cache_row = cache_row
        dialog.concurrency_spin = concurrency_spin
        dialog.warmup_spin = warmup_spin

        def sync_preferences(_dialog: Adw.Dialog) -> None:
            """Keep the in-memory settings aligned with the dialog state."""
            self.cache_enabled = dialog.cache_row.get_active()
            self.concurrency_value = int(dialog.concurrency_spin.get_value())
            self.warmup_queries_value = int(dialog.warmup_spin.get_value())

        dialog.connect("closed", sync_preferences)
        self.preferences_dialog = dialog
        return dialog

    def show_preferences_dialog(self) -> None:
        """Present the shared preferences dialog and sync its current values."""
        dialog = self._ensure_preferences_dialog()
        dialog.cache_row.set_active(self.cache_enabled)
        dialog.concurrency_spin.set_value(self.concurrency_value)
        dialog.warmup_spin.set_value(self.warmup_queries_value)
        dialog.present(self)

    def _group_subtitle(self, group: DnsProfileGroup) -> str:
        """Build a compact subtitle for one provider/profile card."""
        return f"{group.profile_name} · {group_transport_summary(group)}"

    def _variant_subtitle(self, target: str) -> str:
        """Keep the nested transport row subtitle focused on the endpoint."""
        return target

    def _variant_rows_for_group(self, group_row: Adw.ExpanderRow) -> list[Adw.ExpanderRow]:
        """Return the transport rows currently attached to one provider/profile card."""
        return list(getattr(group_row, "dns_variant_rows", []))

    def _update_group_summary(self, group_row: Adw.ExpanderRow) -> None:
        """Summarize the latest transport results at the provider/profile level."""
        summary_row = getattr(group_row, "profile_result_row")
        variant_rows = self._variant_rows_for_group(group_row)
        measured_variants = [
            (variant_row, getattr(variant_row, "latest_benchmark_result", None))
            for variant_row in variant_rows
            if getattr(variant_row, "latest_benchmark_result", None) is not None
        ]

        if not measured_variants:
            summary_row.set_title("Profile Results")
            summary_row.set_subtitle("Test all variants to compare transports inside this profile")
            return

        successful_variants = [
            (variant_row, result)
            for variant_row, result in measured_variants
            if result.error is None and result.average_latency_ms is not None
        ]
        failed_variants = len(measured_variants) - len(successful_variants)
        tested_count = len(measured_variants)
        total_count = len(variant_rows)

        if successful_variants:
            best_variant_row, best_result = min(
                successful_variants,
                key=lambda item: (
                    item[1].average_latency_ms if item[1].average_latency_ms is not None else float("inf"),
                    item[1].p95_latency_ms if item[1].p95_latency_ms is not None else float("inf"),
                ),
            )
            summary_parts = [
                f"Best {best_variant_row.dns_transport}",
                best_result.summary_line(),
                f"tested {tested_count}/{total_count}",
            ]
            if failed_variants:
                summary_parts.append(f"failed {failed_variants}")
            summary_row.set_title("Profile Results")
            summary_row.set_subtitle(" | ".join(summary_parts))
            return

        summary_row.set_title("Profile Results")
        summary_row.set_subtitle(f"tested {tested_count}/{total_count} | failed {failed_variants}")

    def _transport_detail_title(self, transport: str) -> str:
        """Return the appropriate title for the optional transport-specific field."""
        if transport == "DoT":
            return "TLS Hostname"
        return "DoH Method"

    def _is_ip_address(self, value: str) -> bool:
        """Return whether the provided string is a valid IPv4 or IPv6 address."""
        try:
            ipaddress.ip_address(value)
        except ValueError:
            return False
        return True

    def _is_https_url(self, value: str) -> bool:
        """Return whether the provided string is a valid HTTPS URL."""
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)

    def _is_hostname(self, value: str) -> bool:
        """Return whether the provided string looks like a hostname."""
        if not value or "://" in value or "/" in value or " " in value:
            return False
        return True

    def _benchmark_options(self) -> BenchmarkOptions:
        """Collect the current shared benchmark settings from the UI."""
        return BenchmarkOptions(
            query_type=self.test_record_type,
            concurrency=self.concurrency_value,
            warmup_queries=self.warmup_queries_value,
            cache_enabled=self.cache_enabled,
        )

    def _benchmark_endpoint(self, expander_row: Adw.ExpanderRow) -> ResolverEndpoint:
        """Build the benchmark endpoint consumed by the transport engine."""
        return ResolverEndpoint(
            name=getattr(expander_row, "dns_display_name", expander_row.get_title()),
            transport=getattr(expander_row, "dns_transport", "Do53"),
            target=getattr(expander_row, "dns_target", ""),
            tls_hostname=getattr(expander_row, "dns_server_name", None),
            bootstrap_address=getattr(expander_row, "dns_resolved_target", None),
            doh_method=getattr(expander_row, "dns_doh_method", "POST"),
        )

    def _transport_detail_line(self, result) -> str:
        """Render transport-specific metrics in a single line."""
        detail_parts: list[str] = []
        if result.resolved_target and result.resolved_target != result.target:
            detail_parts.append(f"ip {result.resolved_target}")
        if result.connection_setup_ms is not None:
            detail_parts.append(f"connect {result.connection_setup_ms:.1f} ms")
        if result.average_ttfb_ms is not None:
            detail_parts.append(f"TTFB {result.average_ttfb_ms:.1f} ms")
        if result.http_version:
            detail_parts.append(result.http_version)
        return " | ".join(detail_parts) if detail_parts else "No extra transport metrics"

    def _show_error_dialog(self, title: str, message: str) -> None:
        """Present a compact error dialog for local persistence failures."""
        dialog = Adw.Dialog.new()
        dialog.set_title(title)
        dialog.set_content_width(420)
        dialog.set_content_height(180)
        dialog.set_can_close(True)

        content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=18,
            margin_bottom=18,
            margin_start=18,
            margin_end=18,
        )
        message_label = Gtk.Label(
            label=message,
            wrap=True,
            xalign=0.0,
        )
        message_label.add_css_class("dim-label")
        content_box.append(message_label)

        close_button = Gtk.Button(label="Close")
        close_button.add_css_class("suggested-action")
        close_button.connect("clicked", lambda _button: dialog.close())
        content_box.append(close_button)

        dialog.set_child(content_box)
        dialog.present(self)

    def _remove_dns_entry(self, expander_row: Adw.ExpanderRow) -> None:
        """Persist a DNS removal before removing the row from the UI."""
        entry_id = getattr(expander_row, "dns_entry_id")
        is_default = getattr(expander_row, "dns_is_default")

        try:
            if is_default:
                self.dns_store.hide_default_entry(entry_id)
            else:
                self.dns_store.remove_custom_entry(entry_id)
        except OSError as error:
            self._show_error_dialog("Could not save DNS changes", str(error))
            return

        self._reload_dns_rows()

    def _ranked_results(
        self,
        results: list[tuple[str, object]],
    ) -> list[tuple[str, object]]:
        """Sort successful runs by latency and place failed runs at the end."""
        return sorted(
            results,
            key=lambda item: (
                item[1].error is not None or item[1].average_latency_ms is None,
                item[1].average_latency_ms if item[1].average_latency_ms is not None else float("inf"),
                item[1].p95_latency_ms if item[1].p95_latency_ms is not None else float("inf"),
                -(item[1].success_rate or 0.0),
            ),
        )

    def _show_check_all_results_dialog(self, results: list[tuple[str, object]]) -> None:
        """Present the final ranking for a completed Check All run."""
        ranked_results = self._ranked_results(results)
        successful_runs = [result for _name, result in ranked_results if result.error is None]
        failed_runs = len(ranked_results) - len(successful_runs)

        dialog = Adw.Dialog.new()
        dialog.set_title("Check All Results")
        dialog.set_content_width(680)
        dialog.set_content_height(760)
        dialog.set_can_close(True)

        toolbar_view = Adw.ToolbarView()
        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        summary_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=18,
            margin_bottom=6,
            margin_start=18,
            margin_end=18,
        )
        summary_title = Gtk.Label(
            label="Ranking completed",
            xalign=0.0,
        )
        summary_title.add_css_class("title-3")
        summary_box.append(summary_title)

        summary_description = Gtk.Label(
            label=(
                f"{len(successful_runs)} successful benchmarks, {failed_runs} failed. "
                "Resolvers are ordered from best to worst using average latency and p95."
            ),
            wrap=True,
            xalign=0.0,
        )
        summary_description.add_css_class("dim-label")
        summary_box.append(summary_description)

        ranking_group = Adw.PreferencesGroup(
            title="Final Ranking",
            description="Use this ranking only when the compared rows belong to the same provider/backend family.",
        )

        for position, (name, result) in enumerate(ranked_results, start=1):
            row = Adw.ActionRow(
                title=f"{position}. {name}",
                subtitle=f"{result.summary_line()}\n{result.detail_line()}",
                activatable=False,
                selectable=False,
            )
            ranking_group.add(row)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.append(summary_box)

        scrolled_window = Gtk.ScrolledWindow(
            hexpand=True,
            vexpand=True,
            min_content_height=420,
        )
        preferences_page = Adw.PreferencesPage()
        preferences_page.add(ranking_group)
        scrolled_window.set_child(preferences_page)
        content_box.append(scrolled_window)

        toolbar_view.set_content(content_box)
        dialog.set_child(toolbar_view)
        dialog.present(self)

    def _finish_check_all_batch(self, batch_id: int) -> None:
        """Re-enable the bulk action button and show the final batch ranking."""
        if batch_id != self.check_all_batch_id:
            return
        self.check_button.set_sensitive(True)
        if self.check_all_results:
            self._show_check_all_results_dialog(self.check_all_results)
        self.check_all_results = []
        self.check_all_pending = 0

    def _run_group_tests(self, group_row: Adw.ExpanderRow) -> None:
        """Benchmark every transport variant that belongs to one provider/profile card."""
        group_row.set_expanded(True)
        for variant_row in self._variant_rows_for_group(group_row):
            self._run_test_async(None, variant_row)

    def _build_variant_row(self, group_row: Adw.ExpanderRow, entry: DnsEntry) -> Adw.ExpanderRow:
        """Create one nested transport row inside a provider/profile group."""
        variant_row = Adw.ExpanderRow(
            title=entry.transport,
            subtitle=self._variant_subtitle(entry.target),
            activatable=False,
            selectable=False,
        )
        # Variant metadata keeps benchmark logic independent from the nested UI layout.
        variant_row.dns_entry_id = entry.id
        variant_row.dns_is_default = entry.is_default
        variant_row.dns_provider_name = entry.provider_name
        variant_row.dns_profile_name = entry.profile_name
        variant_row.dns_display_name = variant_display_name(entry)
        variant_row.dns_regions = list(entry.regions)
        variant_row.dns_target = entry.target
        variant_row.dns_transport = entry.transport
        variant_row.dns_server_name = entry.tls_hostname
        variant_row.dns_doh_method = entry.doh_method
        variant_row.dns_resolved_target = None
        variant_row.dns_group_row = group_row
        variant_row.latest_result_json = None
        variant_row.latest_benchmark_result = None

        remove_button = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        remove_button.add_css_class("destructive-action")
        remove_button.add_css_class("flat")
        remove_button.set_tooltip_text("Remove variant")
        remove_button.connect("clicked", lambda _btn: self._remove_dns_entry(variant_row))

        endpoint_row = Adw.ActionRow(
            title="Endpoint",
            subtitle=entry.target,
            activatable=False,
            selectable=False,
        )
        transport_row = Adw.ActionRow(
            title="Transport",
            subtitle=entry.transport,
            activatable=False,
            selectable=False,
        )
        variant_row.add_row(endpoint_row)
        variant_row.add_row(transport_row)

        detail_value = None
        if entry.transport == "DoT" and entry.tls_hostname and entry.tls_hostname != entry.target:
            detail_value = entry.tls_hostname
        if entry.transport == "DoH":
            detail_value = entry.doh_method
        if detail_value:
            detail_row = Adw.ActionRow(
                title=self._transport_detail_title(entry.transport),
                subtitle=detail_value,
                activatable=False,
                selectable=False,
            )
            variant_row.add_row(detail_row)

        result_row = Adw.ActionRow(
            title="Results pending",
            subtitle="",
            activatable=False,
            selectable=False,
        )
        metrics_row = Adw.ActionRow(
            title="Metrics",
            subtitle="First query, cache mode, and worker settings will appear here",
            activatable=False,
            selectable=False,
        )
        transport_metrics_row = Adw.ActionRow(
            title="Transport Metrics",
            subtitle="Connection and protocol details will appear here",
            activatable=False,
            selectable=False,
        )

        variant_row.result_row = result_row
        variant_row.metrics_row = metrics_row
        variant_row.transport_metrics_row = transport_metrics_row

        test_button = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        test_button.add_css_class("flat")
        test_button.set_tooltip_text("Test this transport")
        test_button.connect("clicked", self._run_test_async, variant_row)
        result_row.add_suffix(test_button)

        copy_button = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
        copy_button.add_css_class("flat")
        copy_button.set_tooltip_text("Copy benchmark JSON")
        copy_button.set_sensitive(False)

        def copy_json(_button: Gtk.Button) -> None:
            """Copy the latest structured result so runs can be exported elsewhere."""
            latest_result_json = getattr(variant_row, "latest_result_json", None)
            if latest_result_json:
                # GTK4 clipboard APIs consume typed values instead of the GTK3-style set_text helper.
                clipboard_value = GObject.Value()
                clipboard_value.init(str)
                clipboard_value.set_string(latest_result_json)
                self.get_display().get_clipboard().set(clipboard_value)

        copy_button.connect("clicked", copy_json)
        transport_metrics_row.add_suffix(copy_button)
        variant_row.copy_button = copy_button

        variant_row.add_row(result_row)
        variant_row.add_row(metrics_row)
        variant_row.add_row(transport_metrics_row)
        variant_row.add_suffix(remove_button)
        return variant_row

    def _add_group_row(self, group: DnsProfileGroup) -> None:
        """Create one top-level card per provider/profile pair."""
        group_row = Adw.ExpanderRow(
            title=group_display_name(group),
            subtitle=self._group_subtitle(group),
            activatable=False,
            selectable=False,
        )
        group_row.dns_provider_name = group.provider_name
        group_row.dns_profile_name = group.profile_name
        group_row.dns_variant_rows = []

        profile_row = Adw.ActionRow(
            title="Profile",
            subtitle=group.profile_name,
            activatable=False,
            selectable=False,
        )
        transports_row = Adw.ActionRow(
            title="Available Transports",
            subtitle=group_transport_summary(group),
            activatable=False,
            selectable=False,
        )
        group_row.add_row(profile_row)
        group_row.add_row(transports_row)

        if group.regions:
            region_row = Adw.ActionRow(
                title="Origin",
                subtitle=format_region_summary(group.regions),
                activatable=False,
                selectable=False,
            )
            group_row.add_row(region_row)

        profile_result_row = Adw.ActionRow(
            title="Profile Results",
            subtitle="Test all variants to compare transports inside this profile",
            activatable=False,
            selectable=False,
        )
        group_test_button = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        group_test_button.add_css_class("flat")
        group_test_button.set_tooltip_text("Test this profile")
        group_test_button.connect("clicked", lambda _button: self._run_group_tests(group_row))
        group_row.add_suffix(group_test_button)
        group_row.profile_result_row = profile_result_row
        group_row.add_row(profile_result_row)

        for entry in group.entries:
            variant_row = self._build_variant_row(group_row, entry)
            group_row.dns_variant_rows.append(variant_row)
            group_row.add_row(variant_row)
            self.variant_rows.append(variant_row)

        self.group_rows.append(group_row)
        self.list_box.append(group_row)
        self._update_group_summary(group_row)

    def _show_add_dialog(self) -> None:
        """Show an Adwaita dialog asking for resolver settings, then append a row on confirm."""
        dialog = Adw.Dialog.new()
        dialog.set_title("Add DNS Entry")
        dialog.set_content_width(420)
        dialog.set_content_height(460)
        dialog.set_can_close(True)

        content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        provider_row = Adw.EntryRow(title="Provider")
        profile_row = Adw.EntryRow(title="Profile")
        profile_row.set_text("Default")
        target_row = Adw.EntryRow(title="IP Address, Hostname, or HTTPS URL")

        transport_model = Gtk.StringList()
        for transport in TRANSPORTS:
            transport_model.append(transport)
        transport_dropdown = Gtk.DropDown(model=transport_model)
        transport_action_row = Adw.ActionRow(
            title="Transport",
            subtitle="Standard DNS over UDP/TCP on port 53",
            activatable=False,
            selectable=False,
        )
        transport_action_row.add_suffix(transport_dropdown)

        tls_row = Adw.EntryRow(title="TLS Hostname (optional)")
        tls_row.set_visible(False)

        doh_method_model = Gtk.StringList()
        for method in DOH_METHODS:
            doh_method_model.append(method)
        doh_method_dropdown = Gtk.DropDown(model=doh_method_model)
        doh_method_row = Adw.ActionRow(
            title="DoH Method",
            subtitle="RFC 8484 transport method",
            activatable=False,
            selectable=False,
        )
        doh_method_row.add_suffix(doh_method_dropdown)
        doh_method_row.set_visible(False)

        content_box.append(provider_row)
        content_box.append(profile_row)
        content_box.append(target_row)
        content_box.append(transport_action_row)
        content_box.append(tls_row)
        content_box.append(doh_method_row)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, hexpand=True)
        button_box.set_homogeneous(True)
        cancel_btn = Gtk.Button(label="_Cancel", use_underline=True, hexpand=True)
        add_btn = Gtk.Button(label="_Add", use_underline=True, hexpand=True)
        add_btn.add_css_class("suggested-action")
        button_box.append(cancel_btn)
        button_box.append(add_btn)
        content_box.append(button_box)
        dialog.set_child(content_box)

        def close_dialog(_button: Gtk.Button) -> None:
            """Close the dialog without adding a row."""
            dialog.close()

        def update_transport_ui(*_args) -> None:
            """Refresh labels so the dialog matches the selected transport."""
            transport = TRANSPORTS[transport_dropdown.get_selected()]
            target_row.remove_css_class("error")
            tls_row.remove_css_class("error")
            if transport == "Do53":
                target_row.set_title("IP Address or Hostname")
                transport_action_row.set_subtitle("Classic UDP/TCP recursive DNS")
                tls_row.set_visible(False)
                doh_method_row.set_visible(False)
                return
            if transport == "DoT":
                target_row.set_title("IP Address or Hostname")
                transport_action_row.set_subtitle("DNS over TLS on port 853")
                tls_row.set_visible(True)
                doh_method_row.set_visible(False)
                return
            target_row.set_title("HTTPS URL")
            transport_action_row.set_subtitle("DNS over HTTPS with connection reuse")
            tls_row.set_visible(False)
            doh_method_row.set_visible(True)

        def maybe_autoselect_transport(*_args) -> None:
            """Switch to DoH automatically when the endpoint clearly is a HTTPS URL."""
            if self._is_https_url(target_row.get_text().strip()):
                transport_dropdown.set_selected(TRANSPORTS.index("DoH"))

        def confirm_dialog(_button: Gtk.Button | None = None) -> None:
            """Validate the row settings and add the resolver when they are coherent."""
            provider_name = provider_row.get_text().strip()
            profile_name = profile_row.get_text().strip() or "Default"
            target = target_row.get_text().strip()
            transport = TRANSPORTS[transport_dropdown.get_selected()]
            tls_hostname = tls_row.get_text().strip() or None
            doh_method = DOH_METHODS[doh_method_dropdown.get_selected()]

            provider_row.remove_css_class("error")
            profile_row.remove_css_class("error")
            target_row.remove_css_class("error")
            tls_row.remove_css_class("error")

            if not provider_name:
                provider_row.add_css_class("error")
                return
            if transport in ("Do53", "DoT") and not (self._is_ip_address(target) or self._is_hostname(target)):
                target_row.add_css_class("error")
                return
            if transport == "DoH" and not self._is_https_url(target):
                target_row.add_css_class("error")
                return
            if transport == "DoT" and tls_hostname and not self._is_hostname(tls_hostname):
                tls_row.add_css_class("error")
                return

            if provider_name and profile_name and target:
                try:
                    entry = self.dns_store.add_custom_entry(
                        provider_name,
                        profile_name,
                        [],
                        target,
                        transport,
                        tls_hostname,
                        doh_method,
                    )
                except OSError as error:
                    self._show_error_dialog("Could not save DNS changes", str(error))
                    return

                del entry
                self._reload_dns_rows()
                dialog.close()

        cancel_btn.connect("clicked", close_dialog)
        add_btn.connect("clicked", confirm_dialog)
        transport_dropdown.connect("notify::selected", update_transport_ui)
        target_row.connect("notify::text", maybe_autoselect_transport)
        provider_row.connect("activate", confirm_dialog)
        profile_row.connect("activate", confirm_dialog)
        target_row.connect("activate", confirm_dialog)
        dialog.set_default_widget(add_btn)
        update_transport_ui()
        dialog.present(self)

    @Gtk.Template.Callback()
    def on_add_button_clicked(self, _button: Gtk.Button) -> None:
        """Open a dialog to capture resolver settings, then append a new entry row."""
        self._show_add_dialog()

    @Gtk.Template.Callback()
    def on_check_button_clicked(self, _button: Gtk.Button) -> None:
        """Run all resolver benchmarks with the shared benchmark settings."""
        rows = list(self.variant_rows)
        if not rows:
            return

        self.check_all_batch_id += 1
        self.check_all_pending = len(rows)
        self.check_all_results = []
        self.check_button.set_sensitive(False)

        for row in rows:
            self._run_test_async(None, row, batch_id=self.check_all_batch_id)

    def _run_test_async(
        self,
        _button: Gtk.Button | None,
        expander_row: Adw.ExpanderRow,
        batch_id: int | None = None,
    ) -> None:
        """Execute the benchmark in a worker thread and update the row from the GTK main loop."""
        result_row = getattr(expander_row, "result_row")
        metrics_row = getattr(expander_row, "metrics_row")
        transport_metrics_row = getattr(expander_row, "transport_metrics_row")
        copy_button = getattr(expander_row, "copy_button")
        group_row = getattr(expander_row, "dns_group_row", None)
        endpoint = self._benchmark_endpoint(expander_row)
        options = self._benchmark_options()

        result_row.set_title("Testing...")
        result_row.set_subtitle("Preparing transport benchmark...")
        metrics_row.set_title("Metrics")
        metrics_row.set_subtitle("Waiting for results...")
        transport_metrics_row.set_title("Transport Metrics")
        transport_metrics_row.set_subtitle("Waiting for results...")
        copy_button.set_sensitive(False)
        expander_row.set_expanded(True)
        self.list_box.queue_draw()

        def worker() -> None:
            def update_progress(phase: str, current: int, total: int, detail: str) -> bool:
                """Reflect benchmark progress in the row while the worker thread is running."""
                if phase == "preflight":
                    result_row.set_title("Testing... preflight")
                    result_row.set_subtitle(detail)
                elif phase == "warmup":
                    result_row.set_title(f"Testing... warm-up {current}/{total}")
                    result_row.set_subtitle(detail)
                elif phase == "cache":
                    result_row.set_title("Testing... cache prime")
                    result_row.set_subtitle(detail)
                else:
                    result_row.set_title(f"Testing... {current}/{total}")
                    result_row.set_subtitle(detail)
                result_row.queue_draw()
                return False

            try:
                result = run_benchmark_sync(
                    endpoint,
                    TOP_ES_WEBS,
                    options,
                    progress_callback=lambda phase, current, total, detail: GLib.idle_add(
                        update_progress,
                        phase,
                        current,
                        total,
                        detail,
                    ),
                )
            except Exception as error:
                result = None
                error_text = f"{type(error).__name__}: {error}"

            def update_ui() -> bool:
                """Publish the final benchmark result after the worker thread finishes."""
                if result is None:
                    failure_result = BenchmarkResult(
                        protocol=endpoint.transport,
                        endpoint=endpoint.target,
                        target=endpoint.target,
                        cache_mode=options.cache_mode,
                        warmup_queries=options.warmup_queries,
                        concurrency=options.concurrency,
                        first_query_latency_ms=None,
                        average_latency_ms=None,
                        p95_latency_ms=None,
                        success_rate=0.0,
                        successful_queries=0,
                        total_queries=len(TOP_ES_WEBS),
                        resolved_target=endpoint.bootstrap_address,
                        error=error_text,
                    )
                    expander_row.latest_benchmark_result = failure_result
                    expander_row.latest_result_json = None
                    result_row.set_title("Result")
                    result_row.set_subtitle(error_text)
                    metrics_row.set_title("Metrics")
                    metrics_row.set_subtitle("Benchmark aborted")
                    transport_metrics_row.set_title("Transport Metrics")
                    transport_metrics_row.set_subtitle("No transport details collected")
                    copy_button.set_sensitive(False)
                    if group_row is not None:
                        self._update_group_summary(group_row)
                    if batch_id is not None and batch_id == self.check_all_batch_id:
                        self.check_all_results.append(
                            (
                                getattr(expander_row, "dns_display_name", expander_row.get_title()),
                                failure_result,
                            )
                        )
                        self.check_all_pending -= 1
                        if self.check_all_pending == 0:
                            self._finish_check_all_batch(batch_id)
                    return False

                expander_row.dns_resolved_target = result.resolved_target
                expander_row.latest_benchmark_result = result
                expander_row.latest_result_json = result.to_json()
                result_row.set_title("Result")
                result_row.set_subtitle(result.summary_line())
                metrics_row.set_title("Metrics")
                metrics_row.set_subtitle(result.detail_line())
                transport_metrics_row.set_title("Transport Metrics")
                transport_metrics_row.set_subtitle(self._transport_detail_line(result))
                copy_button.set_sensitive(True)
                result_row.add_css_class("property")
                if group_row is not None:
                    self._update_group_summary(group_row)
                expander_row.queue_draw()
                self.list_box.queue_draw()
                if not self._printed_console_header:
                    print("[DNS benchmark]", flush=False)
                    print(result.table_header(), flush=False)
                    self._printed_console_header = True
                print(result.table_row(), flush=True)
                if batch_id is not None and batch_id == self.check_all_batch_id:
                    self.check_all_results.append(
                        (getattr(expander_row, "dns_display_name", expander_row.get_title()), result)
                    )
                    self.check_all_pending -= 1
                    if self.check_all_pending == 0:
                        self._finish_check_all_batch(batch_id)
                return False

            GLib.idle_add(update_ui)

        threading.Thread(target=worker, daemon=True).start()
