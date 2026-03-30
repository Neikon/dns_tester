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
import importlib.util
import socket
import threading
import time
from urllib.parse import urlparse

import dns.nameserver
import dns.query
import dns.resolver
from gi.repository import GLib
from .aux import TOP_ES_WEBS
from .default_dns import DEFAULT_DNS
from gi.repository import Adw
from gi.repository import Gtk

# Supported resolver transports exposed in the add-entry dialog.
TRANSPORTS = ("Do53", "DoT", "DoH")
# DoH requires the optional httpx dependency in dnspython.
HAS_HTTPX = importlib.util.find_spec("httpx") is not None
# Keep individual attempts short and cap the whole resolver test so the UI stays responsive.
QUERY_LIFETIME_SECONDS = 1.0
RESOLVER_TIME_BUDGET_SECONDS = 15.0
# Probe the resolver first so transport/setup failures stop immediately.
RESOLVER_PROBE_TIMEOUT_SECONDS = 2.5
RESOLVER_PROBE_DOMAIN = "."
RESOLVER_PROBE_RECORD_TYPE = "NS"
# Try newer DoH transports first, then degrade to the broadest compatibility mode.
DOH_HTTP_VERSIONS = (
    dns.query.HTTPVersion.H3,
    dns.query.HTTPVersion.H2,
    dns.query.HTTPVersion.DEFAULT,
)

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
        for name, target, transport, server_name in DEFAULT_DNS:
            self._add_row(name, target, transport, server_name)

        # Insert the list box into the main container.
        self.content_box.append(self.list_box)

    def _transport_details_title(self, transport: str) -> str:
        """Return the label for the transport-specific extra field."""
        if transport == "DoT":
            return "TLS Hostname"
        return "Bootstrap IP"

    def _transport_summary(self, transport: str, target: str) -> str:
        """Build a compact subtitle for the expander row."""
        return f"{transport} | {target}"

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

    def _resolve_endpoint_address(self, target: str, port: int) -> str:
        """Resolve a hostname to an IP address when the transport requires a socket destination."""
        if self._is_ip_address(target):
            return target

        # Use the system resolver only as bootstrap so users can enter hostnames directly.
        for family, socktype, proto, _canonname, sockaddr in socket.getaddrinfo(target, port, type=socket.SOCK_STREAM):
            if family in (socket.AF_INET, socket.AF_INET6) and socktype == socket.SOCK_STREAM and proto:
                return sockaddr[0]

        raise RuntimeError(f"Could not resolve address for {target}")

    def _resolve_transport_target(self, target: str, transport: str, server_name: str | None) -> tuple[str, str | None]:
        """Resolve transport-specific connection details and return the socket address plus hostname."""
        if transport == "Do53":
            return self._resolve_endpoint_address(target, 53), None
        if transport == "DoT":
            hostname = server_name
            if not hostname and self._is_hostname(target):
                hostname = target
            return self._resolve_endpoint_address(target, 853), hostname
        return target, server_name

    def _build_nameserver(
        self,
        target: str,
        transport: str,
        server_name: str | None,
        resolved_target: str | None = None,
    ) -> dns.nameserver.Nameserver:
        """Create the appropriate dnspython nameserver object for the selected transport."""
        if transport == "Do53":
            return dns.nameserver.Do53Nameserver(resolved_target or self._resolve_endpoint_address(target, 53))
        if transport == "DoT":
            return dns.nameserver.DoTNameserver(
                resolved_target or self._resolve_endpoint_address(target, 853),
                port=853,
                hostname=server_name,
            )
        if transport == "DoH":
            if not HAS_HTTPX:
                raise RuntimeError("DoH requires the optional httpx dependency")
            # Use H3 first; DoH fallback across versions is handled per query attempt.
            return dns.nameserver.DoHNameserver(
                target,
                http_version=dns.query.HTTPVersion.H3,
            )
        raise ValueError(f"Unsupported transport: {transport}")

    def _resolve_single_domain(
        self,
        resolver: dns.resolver.Resolver,
        domain: str,
        transport: str,
        target: str,
        remaining_budget: float,
        record_type: str | None = None,
        preferred_http_version=None,
    ):
        """Resolve one domain, retrying DoH with lower HTTP versions when needed."""
        last_error: Exception | None = None
        selected_http_version = None
        query_record_type = record_type or self.test_record_type

        if transport != "DoH":
            answer = resolver.resolve(
                domain,
                query_record_type,
                lifetime=min(resolver.lifetime, remaining_budget),
            )
            return answer, selected_http_version

        original_nameserver = resolver.nameservers[0]
        http_versions = DOH_HTTP_VERSIONS
        if preferred_http_version is not None:
            http_versions = (preferred_http_version,)

        for http_version in http_versions:
            try:
                resolver.nameservers = [
                    dns.nameserver.DoHNameserver(
                        target,
                        http_version=http_version,
                    )
                ]
                answer = resolver.resolve(
                    domain,
                    query_record_type,
                    lifetime=min(resolver.lifetime, remaining_budget),
                )
                selected_http_version = http_version.name
                return answer, selected_http_version
            except Exception as error:
                last_error = error
                print(
                    f"[DNS check] DoH fallback {target} {domain} failed on {http_version.name}: {error}",
                    flush=True,
                )
        resolver.nameservers = [original_nameserver]
        assert last_error is not None
        raise last_error

    def _probe_resolver(self, resolver: dns.resolver.Resolver, transport: str, target: str):
        """Run a fast resolver probe so endpoint failures surface before the full benchmark."""
        start_time = time.monotonic()
        answer, selected_http_version = self._resolve_single_domain(
            resolver,
            RESOLVER_PROBE_DOMAIN,
            transport,
            target,
            RESOLVER_PROBE_TIMEOUT_SECONDS,
            record_type=RESOLVER_PROBE_RECORD_TYPE,
        )
        latency_ms = (time.monotonic() - start_time) * 1000.0
        return answer, selected_http_version, latency_ms

    def _add_row(self, name: str, target: str, transport: str, server_name: str | None = None) -> None:
        """Create and append an expander row with the given resolver settings."""
        expander_row = Adw.ExpanderRow(
            title=name,
            subtitle=self._transport_summary(transport, target),
            activatable=False,
            selectable=False,
        )
        # Store the resolver settings on the row so test actions do not depend on UI labels.
        expander_row.dns_target = target
        expander_row.dns_transport = transport
        expander_row.dns_server_name = server_name
        expander_row.dns_resolved_target = None

        remove_button = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        remove_button.add_css_class("destructive-action")
        remove_button.add_css_class("flat")
        remove_button.set_tooltip_text("Remove entry")
        remove_button.connect(
            "clicked",
            lambda _btn: self.list_box.remove(expander_row),
        )
        # Configuration rows keep the transport details visible when the row is expanded.
        endpoint_row = Adw.ActionRow(
            title="Endpoint",
            subtitle=target,
            activatable=False,
            selectable=False,
        )
        transport_row = Adw.ActionRow(
            title="Transport",
            subtitle=transport,
            activatable=False,
            selectable=False,
        )
        expander_row.add_row(endpoint_row)
        expander_row.add_row(transport_row)
        if server_name and server_name != target:
            extra_row = Adw.ActionRow(
                title=self._transport_details_title(transport),
                subtitle=server_name,
                activatable=False,
                selectable=False,
            )
            expander_row.add_row(extra_row)

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
        """Show an Adwaita dialog asking for resolver settings, then append a row on confirm."""
        dialog = Adw.Dialog.new()
        dialog.set_title("Add DNS Entry")
        dialog.set_content_width(360)
        dialog.set_content_height(320)
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
        target_row = Adw.EntryRow(title="IP Address, Hostname, or HTTPS URL")
        # A dropdown keeps transport selection explicit instead of guessing from the input.
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

        content_box.append(name_row)
        content_box.append(target_row)
        content_box.append(transport_action_row)

        # Action buttons to cancel or confirm the dialog; stretched to share full width.
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
            """Refresh dialog labels so the required input matches the selected transport."""
            transport = TRANSPORTS[transport_dropdown.get_selected()]
            target_row.remove_css_class("error")
            if transport == "Do53":
                target_row.set_title("IP Address or Hostname")
                transport_action_row.set_subtitle("Standard DNS over UDP/TCP on port 53")
                return
            if transport == "DoT":
                target_row.set_title("IP Address or Hostname")
                transport_action_row.set_subtitle("Encrypted DNS over TLS on port 853")
                return
            target_row.set_title("HTTPS URL")
            if HAS_HTTPX:
                transport_action_row.set_subtitle("Encrypted DNS over HTTPS")
            else:
                transport_action_row.set_subtitle("Encrypted DNS over HTTPS (httpx missing)")

        def maybe_autoselect_transport(*_args) -> None:
            """Switch to DoH automatically when the endpoint clearly is a HTTPS URL."""
            if self._is_https_url(target_row.get_text().strip()):
                transport_dropdown.set_selected(TRANSPORTS.index("DoH"))

        def confirm_dialog(_button: Gtk.Button | None = None) -> None:
            """Add the row if data is valid and close the dialog."""
            name = name_row.get_text().strip()
            target = target_row.get_text().strip()
            transport = TRANSPORTS[transport_dropdown.get_selected()]

            target_row.remove_css_class("error")

            # Standard DNS and DoT accept either a raw IP or a hostname that we bootstrap locally.
            if transport in ("Do53", "DoT") and not (self._is_ip_address(target) or self._is_hostname(target)):
                target_row.add_css_class("error")
                return
            if transport == "DoH" and not self._is_https_url(target):
                target_row.add_css_class("error")
                return

            if name and target:
                self._add_row(name, target, transport, None)
                dialog.close()

        cancel_btn.connect("clicked", close_dialog)
        add_btn.connect("clicked", confirm_dialog)
        transport_dropdown.connect("notify::selected", update_transport_ui)
        target_row.connect("notify::text", maybe_autoselect_transport)
        name_row.connect("activate", confirm_dialog)
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
        """Run individual checks sequentially and update each row inline."""
        row = self.list_box.get_first_child()
        print("[DNS check] Running all rows...")
        while row is not None:
            if isinstance(row, Adw.ExpanderRow):
                result_row = getattr(row, "result_row", None)
                if isinstance(result_row, Adw.ActionRow):
                    self._run_test_async(None, row, result_row)
            row = row.get_next_sibling()

    def _resolve_dns(
        self,
        target: str,
        transport: str,
        server_name: str | None,
        resolved_target: str | None = None,
        progress_callback=None,
    ) -> tuple[str, str | None]:
        """Resolve many domains via the given DNS server and report latency stats."""
        resolver = dns.resolver.Resolver(configure=False)
        resolver.lifetime = QUERY_LIFETIME_SECONDS
        try:
            if resolved_target is None:
                resolved_target, server_name = self._resolve_transport_target(target, transport, server_name)
            resolver.nameservers = [self._build_nameserver(target, transport, server_name, resolved_target)]
        except Exception as error:
            return f"{type(error).__name__}: {error}", resolved_target

        latencies: list[float] = []
        errors = 0
        last_error: Exception | None = None
        tested = 0
        total = len(TOP_ES_WEBS)
        start_time = time.monotonic()
        used_http_version = None

        print(f"[DNS check] Start {transport} {target}", flush=True)
        if progress_callback is not None:
            progress_callback(-1, total, "Resolver preflight")

        try:
            _probe_answer, selected_http_version, probe_latency_ms = self._probe_resolver(
                resolver,
                transport,
                target,
            )
            if selected_http_version is not None:
                used_http_version = selected_http_version
                resolver.nameservers = [
                    dns.nameserver.DoHNameserver(
                        target,
                        http_version=dns.query.HTTPVersion[selected_http_version],
                    )
                ]
            print(
                f"[DNS check] Preflight OK {transport} {target}: {probe_latency_ms:.1f} ms",
                flush=True,
            )
        except Exception as error:
            print(f"[DNS check] Preflight failed {transport} {target}: {error}", flush=True)
            return f"preflight failed: {type(error).__name__}: {error}", resolved_target

        for domain in TOP_ES_WEBS:
            elapsed = time.monotonic() - start_time
            remaining_budget = RESOLVER_TIME_BUDGET_SECONDS - elapsed
            if remaining_budget <= 0:
                print(
                    f"[DNS check] Budget exceeded for {transport} {target} after {tested}/{total} domains",
                    flush=True,
                )
                break

            if progress_callback is not None:
                progress_callback(tested, total, domain)

            try:
                answer, selected_http_version = self._resolve_single_domain(
                    resolver,
                    domain,
                    transport,
                    target,
                    remaining_budget,
                    preferred_http_version=dns.query.HTTPVersion[used_http_version] if used_http_version else None,
                )
                if selected_http_version is not None:
                    used_http_version = selected_http_version
                latency_ms = (answer.response.time or 0) * 1000.0
                latencies.append(latency_ms)
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout) as error:
                errors += 1
                last_error = error
            except Exception as error:
                errors += 1
                last_error = error
            finally:
                tested += 1

        if not latencies:
            if last_error is not None:
                return f"{type(last_error).__name__}: {last_error}", resolved_target
            if tested < total:
                return f"no successful responses | tested {tested}/{total} within time budget", resolved_target
            return "no successful responses", resolved_target

        best = min(latencies)
        worst = max(latencies)
        avg = sum(latencies) / len(latencies)
        summary = f"avg {avg:.1f} ms | best {best:.1f} ms | worst {worst:.1f} ms"
        if errors:
            summary += f" | errors {errors}"
        if tested < total:
            summary += f" | tested {tested}/{total}"
        if used_http_version is not None:
            summary += f" | {used_http_version}"
        print(f"[DNS check] Finish {transport} {target}: {summary}", flush=True)
        return summary, resolved_target

    def _run_test_async(self, _btn: Gtk.Button | None, expander_row: Adw.ExpanderRow, result_row: Adw.ActionRow) -> None:
        """Resolve only this DNS in a worker thread and update its nested result row."""
        target = getattr(expander_row, "dns_target", "")
        transport = getattr(expander_row, "dns_transport", "Do53")
        server_name = getattr(expander_row, "dns_server_name", None)
        resolved_target = getattr(expander_row, "dns_resolved_target", None)
        if not target:
            result_row.set_title("No server set")
            result_row.set_subtitle("")
            return

        result_row.set_title("Testing...")
        result_row.set_subtitle(f"Working over {transport}...")
        expander_row.set_expanded(True)
        self.list_box.queue_draw()

        def worker() -> None:
            def update_progress(done: int, total: int, domain: str) -> bool:
                """Update the row while the worker is still probing domains."""
                if done < 0:
                    result_row.set_title("Testing... preflight")
                    result_row.set_subtitle(f"{transport} | {domain}")
                    result_row.queue_draw()
                    return False
                result_row.set_title(f"Testing... {done + 1}/{total}")
                result_row.set_subtitle(f"{transport} | {domain}")
                result_row.queue_draw()
                return False

            try:
                result, resolved_value = self._resolve_dns(
                    target,
                    transport,
                    server_name,
                    resolved_target,
                    progress_callback=lambda done, total, domain: GLib.idle_add(
                        update_progress,
                        done,
                        total,
                        domain,
                    ),
                )
            except Exception as error:
                result = f"{type(error).__name__}: {error}"
                resolved_value = resolved_target

            def update_ui() -> bool:
                expander_row.dns_resolved_target = resolved_value
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
