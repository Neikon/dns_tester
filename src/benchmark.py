# benchmark.py
#
# Benchmark engine for fair DNS transport comparisons.
# The engine keeps transport logic away from the GTK layer so benchmarking rules
# can evolve without making the UI code hard to follow.

from __future__ import annotations

import asyncio
import base64
import json
import math
import socket
import ssl
import statistics
import time
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Callable
from typing import Literal
from urllib.parse import parse_qsl
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import urlunparse

import dns.asyncquery
import dns.message
import dns.name
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.resolver
import httpx

# The warm-up is intentionally small; it should heat up transports without dominating the run.
DEFAULT_WARMUP_QUERIES = 5
# The UI should stay responsive, so keep the worker pool bounded.
DEFAULT_CONCURRENCY = 10
# Every query uses the same timeout budget so protocols are compared consistently.
DEFAULT_QUERY_TIMEOUT_SECONDS = 3.0

TransportName = Literal["Do53", "DoT", "DoH"]
DoHMethod = Literal["POST", "GET"]
ProgressCallback = Callable[[str, int, int, str], None]


@dataclass(frozen=True)
class ResolverEndpoint:
    """Configuration required to reach a recursive resolver over one transport."""

    name: str
    transport: TransportName
    target: str
    tls_hostname: str | None = None
    bootstrap_address: str | None = None
    doh_method: DoHMethod = "POST"


@dataclass(frozen=True)
class BenchmarkOptions:
    """Runtime options exposed by the UI."""

    query_type: str = "A"
    timeout_seconds: float = DEFAULT_QUERY_TIMEOUT_SECONDS
    warmup_queries: int = DEFAULT_WARMUP_QUERIES
    concurrency: int = DEFAULT_CONCURRENCY
    cache_enabled: bool = False

    @property
    def cache_mode(self) -> str:
        """Return the human-readable cache mode used in the result view."""
        return "warm" if self.cache_enabled else "cold"


@dataclass
class QueryMeasurement:
    """Per-query timings collected during the measured phase."""

    domain: str
    success: bool
    latency_ms: float | None = None
    ttfb_ms: float | None = None
    from_cache: bool = False
    error: str | None = None
    http_version: str | None = None
    response_wire: bytes | None = None


@dataclass
class BenchmarkResult:
    """Structured summary returned to the GTK layer."""

    protocol: TransportName
    endpoint: str
    target: str
    cache_mode: str
    warmup_queries: int
    concurrency: int
    first_query_latency_ms: float | None
    average_latency_ms: float | None
    p95_latency_ms: float | None
    success_rate: float
    successful_queries: int
    total_queries: int
    connection_setup_ms: float | None = None
    average_ttfb_ms: float | None = None
    http_version: str | None = None
    resolved_target: str | None = None
    error: str | None = None
    measurements: list[QueryMeasurement] = field(default_factory=list)

    def summary_line(self) -> str:
        """Return the compact table-style line shown in the main result row."""
        if self.error:
            return self.error
        return (
            f"avg {self.average_latency_ms:.1f} ms | "
            f"p95 {self.p95_latency_ms:.1f} ms | "
            f"success {self.success_rate:.0f}%"
        )

    def detail_line(self) -> str:
        """Return the secondary metrics line shown below the summary."""
        if self.error:
            return (
                f"mode {self.cache_mode} | warm-up {self.warmup_queries} | "
                f"workers {self.concurrency}"
            )

        detail_parts = [
            f"first {self.first_query_latency_ms:.1f} ms",
            f"mode {self.cache_mode}",
            f"workers {self.concurrency}",
        ]
        if self.connection_setup_ms is not None:
            detail_parts.append(f"connect {self.connection_setup_ms:.1f} ms")
        if self.average_ttfb_ms is not None:
            detail_parts.append(f"TTFB {self.average_ttfb_ms:.1f} ms")
        if self.http_version:
            detail_parts.append(self.http_version)
        return " | ".join(detail_parts)

    def to_json(self) -> str:
        """Serialize the structured benchmark result for optional export/debugging."""
        payload = asdict(self)
        # Raw DNS wire payloads are useful internally, but JSON export should stay portable.
        for measurement in payload["measurements"]:
            response_wire = measurement.pop("response_wire", None)
            measurement["response_size_bytes"] = len(response_wire) if response_wire is not None else None
        return json.dumps(payload, indent=2, sort_keys=True)

    @staticmethod
    def table_header() -> str:
        """Return a fixed-width header for console-friendly benchmark summaries."""
        return (
            f"{'Protocol':<8} {'Cache':<6} {'Avg (ms)':>10} {'P95 (ms)':>10} "
            f"{'First (ms)':>10} {'Success':>8}"
        )

    def table_row(self) -> str:
        """Return a fixed-width data row for console-friendly benchmark summaries."""
        if self.error:
            return (
                f"{self.protocol:<8} {self.cache_mode:<6} {'-':>10} {'-':>10} "
                f"{'-':>10} {'0%':>8}"
            )
        return (
            f"{self.protocol:<8} {self.cache_mode:<6} {self.average_latency_ms:>10.1f} "
            f"{self.p95_latency_ms:>10.1f} {self.first_query_latency_ms:>10.1f} "
            f"{self.success_rate:>7.0f}%"
        )


@dataclass(frozen=True)
class CachedResponse:
    """Cache values store only the DNS wire format so they remain transport-agnostic."""

    wire: bytes
    expiration: float


class ResponseCache:
    """Small wrapper around dnspython's cache so warm benchmarks are explicit."""

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.cache = dns.resolver.Cache()
        # Keep a resolver with an attached cache to match dnspython's documented pattern.
        self.resolver = dns.resolver.Resolver(configure=False)
        self.resolver.cache = self.cache
        self._lock = asyncio.Lock()

    def _make_key(self, domain: str, query_type: str) -> tuple[dns.name.Name, dns.rdatatype.RdataType, dns.rdataclass.RdataClass]:
        """Match dnspython's cache key shape: (qname, rdtype, rdclass)."""
        return (
            dns.name.from_text(domain),
            dns.rdatatype.from_text(query_type),
            dns.rdataclass.IN,
        )

    async def get(self, domain: str, query_type: str) -> QueryMeasurement | None:
        """Return a cached response as an instant warm measurement when available."""
        if not self.enabled:
            return None

        cache_key = self._make_key(domain, query_type)
        lookup_started = time.perf_counter()
        async with self._lock:
            cached = self.cache.get(cache_key)
        if cached is None:
            return None

        latency_ms = (time.perf_counter() - lookup_started) * 1000.0
        return QueryMeasurement(
            domain=domain,
            success=True,
            latency_ms=latency_ms,
            ttfb_ms=None,
            from_cache=True,
        )

    async def put(self, domain: str, query_type: str, message: dns.message.Message) -> None:
        """Store successful responses so the measured phase can run warm."""
        if not self.enabled:
            return

        cache_key = self._make_key(domain, query_type)
        ttl = _message_ttl(message)
        async with self._lock:
            self.cache.put(
                cache_key,
                CachedResponse(
                    wire=message.to_wire(),
                    expiration=time.time() + ttl,
                ),
            )


def _percentile_95(values: list[float]) -> float:
    """Compute a stable p95 even for small datasets."""
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    index = math.ceil(len(sorted_values) * 0.95) - 1
    return sorted_values[max(index, 0)]


def _safe_error(error: Exception) -> str:
    """Normalize exceptions into short UI-friendly messages."""
    return f"{type(error).__name__}: {error}"


def _build_query(domain: str, query_type: str) -> dns.message.QueryMessage:
    """Create a standard recursive DNS question."""
    return dns.message.make_query(domain, query_type)


def _resolved_ip(target: str) -> str | None:
    """Return the IP only when the target already is one."""
    try:
        socket.getaddrinfo(target, None)
    except socket.gaierror:
        return None
    try:
        socket.inet_pton(socket.AF_INET, target)
        return target
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, target)
        return target
    except OSError:
        return None


def _resolve_target_address(target: str, port: int, socket_type: socket.SocketKind) -> str:
    """Resolve a transport endpoint to a concrete IP address when needed."""
    resolved = _resolved_ip(target)
    if resolved is not None:
        return resolved
    return socket.getaddrinfo(target, port, type=socket_type)[0][4][0]


def _message_ttl(message: dns.message.Message) -> int:
    """Return a best-effort TTL for cache bookkeeping during one benchmark run."""
    ttl_candidates = [
        rrset.ttl
        for rrset in [*message.answer, *message.authority, *message.additional]
        if rrset.ttl > 0
    ]
    return min(ttl_candidates) if ttl_candidates else 60


class Do53Worker:
    """Worker that issues classic UDP DNS queries."""

    def __init__(self, endpoint: ResolverEndpoint, options: BenchmarkOptions):
        self.endpoint = endpoint
        self.options = options

    async def query(self, domain: str) -> QueryMeasurement:
        """Resolve one domain over UDP and record the latency."""
        query = _build_query(domain, self.options.query_type)
        started = time.perf_counter()
        try:
            response, _used_tcp = await dns.asyncquery.udp_with_fallback(
                query,
                self.endpoint.target,
                timeout=self.options.timeout_seconds,
                port=53,
            )
        except Exception as error:
            return QueryMeasurement(domain=domain, success=False, error=_safe_error(error))

        latency_ms = (time.perf_counter() - started) * 1000.0
        if response.rcode() != dns.rcode.NOERROR:
            return QueryMeasurement(
                domain=domain,
                success=False,
                latency_ms=latency_ms,
                error=dns.rcode.to_text(response.rcode()),
                response_wire=response.to_wire(),
            )
        return QueryMeasurement(
            domain=domain,
            success=True,
            latency_ms=latency_ms,
            response_wire=response.to_wire(),
        )

    async def close(self) -> None:
        """No persistent state is kept for classic UDP."""


class DoTWorker:
    """Worker that reuses a single TLS connection for sequential DoT queries."""

    def __init__(self, endpoint: ResolverEndpoint, options: BenchmarkOptions):
        self.endpoint = endpoint
        self.options = options
        self.connect_address = endpoint.bootstrap_address or endpoint.target
        self.server_hostname = endpoint.tls_hostname or (endpoint.target if _resolved_ip(endpoint.target) is None else None)
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.connection_setup_ms: float | None = None

    async def _connect(self) -> None:
        """Open the TLS stream once and keep it for subsequent queries."""
        if self.writer is not None and not self.writer.is_closing():
            return

        ssl_context = ssl.create_default_context()
        if self.server_hostname is None:
            ssl_context.check_hostname = False

        started = time.perf_counter()
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(
                host=self.connect_address,
                port=853,
                ssl=ssl_context,
                server_hostname=self.server_hostname,
            ),
            timeout=self.options.timeout_seconds,
        )
        self.connection_setup_ms = (time.perf_counter() - started) * 1000.0

    async def _query_once(self, domain: str) -> QueryMeasurement:
        """Send one DNS message over the persistent TLS stream."""
        await self._connect()
        assert self.reader is not None
        assert self.writer is not None

        query = _build_query(domain, self.options.query_type)
        payload = query.to_wire(prepend_length=True)
        started = time.perf_counter()
        self.writer.write(payload)
        await asyncio.wait_for(self.writer.drain(), timeout=self.options.timeout_seconds)
        size_data = await asyncio.wait_for(self.reader.readexactly(2), timeout=self.options.timeout_seconds)
        expected_size = int.from_bytes(size_data, "big")
        wire = await asyncio.wait_for(self.reader.readexactly(expected_size), timeout=self.options.timeout_seconds)
        response = dns.message.from_wire(wire)
        latency_ms = (time.perf_counter() - started) * 1000.0

        if response.rcode() != dns.rcode.NOERROR:
            return QueryMeasurement(
                domain=domain,
                success=False,
                latency_ms=latency_ms,
                error=dns.rcode.to_text(response.rcode()),
                response_wire=wire,
            )
        return QueryMeasurement(
            domain=domain,
            success=True,
            latency_ms=latency_ms,
            response_wire=wire,
        )

    async def query(self, domain: str) -> QueryMeasurement:
        """Retry once with a fresh TLS socket if the persistent stream was dropped."""
        try:
            return await self._query_once(domain)
        except Exception:
            await self.close()
            try:
                return await self._query_once(domain)
            except Exception as error:
                return QueryMeasurement(domain=domain, success=False, error=_safe_error(error))

    async def close(self) -> None:
        """Close the persistent TLS stream held by this worker."""
        if self.writer is None:
            return
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except Exception:
            pass
        self.reader = None
        self.writer = None


class DoHClient:
    """Shared DoH client that reuses HTTP connections across all queries."""

    def __init__(self, endpoint: ResolverEndpoint, options: BenchmarkOptions):
        self.endpoint = endpoint
        self.options = options
        self.client = httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(options.timeout_seconds),
            headers={"accept": "application/dns-message"},
        )
        self.connection_setup_ms: float | None = None
        self.http_version: str | None = None

    async def measure_connection_setup(self) -> None:
        """Measure the initial TCP/TLS setup separately from the request benchmark."""
        parsed = urlparse(self.endpoint.target)
        host = parsed.hostname
        if host is None:
            return

        port = parsed.port or 443
        ssl_context = ssl.create_default_context()
        started = time.perf_counter()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host=host, port=port, ssl=ssl_context, server_hostname=host),
            timeout=self.options.timeout_seconds,
        )
        self.connection_setup_ms = (time.perf_counter() - started) * 1000.0
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        del reader

    def _request_arguments(self, query: dns.message.QueryMessage) -> tuple[str, str, dict[str, str], bytes | None]:
        """Build a RFC 8484 compatible GET or POST request."""
        wire = query.to_wire()
        headers = {"accept": "application/dns-message"}
        if self.endpoint.doh_method == "POST":
            headers["content-type"] = "application/dns-message"
            return "POST", self.endpoint.target, headers, wire

        parsed = urlparse(self.endpoint.target)
        query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query_items["dns"] = base64.urlsafe_b64encode(wire).rstrip(b"=").decode("ascii")
        request_url = urlunparse(parsed._replace(query=urlencode(query_items)))
        return "GET", request_url, headers, None

    async def query(self, domain: str, query_type: str) -> QueryMeasurement:
        """Execute one DoH exchange and measure both total latency and TTFB."""
        query = _build_query(domain, query_type)
        method, request_url, headers, content = self._request_arguments(query)
        started = time.perf_counter()

        try:
            async with self.client.stream(method, request_url, headers=headers, content=content) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type and content_type != "application/dns-message":
                    raise ValueError(f"unexpected content-type {content_type}")

                first_chunk_started: float | None = None
                payload = bytearray()
                async for chunk in response.aiter_bytes():
                    if first_chunk_started is None:
                        first_chunk_started = time.perf_counter()
                    payload.extend(chunk)

                finished = time.perf_counter()
                ttfb_ms = ((first_chunk_started or finished) - started) * 1000.0
                latency_ms = (finished - started) * 1000.0
                dns_response = dns.message.from_wire(bytes(payload))
                self.http_version = response.http_version.upper().replace("/", "_")
        except Exception as error:
            return QueryMeasurement(domain=domain, success=False, error=_safe_error(error))

        if dns_response.rcode() != dns.rcode.NOERROR:
            return QueryMeasurement(
                domain=domain,
                success=False,
                latency_ms=latency_ms,
                ttfb_ms=ttfb_ms,
                http_version=self.http_version,
                error=dns.rcode.to_text(dns_response.rcode()),
                response_wire=bytes(payload),
            )
        return QueryMeasurement(
            domain=domain,
            success=True,
            latency_ms=latency_ms,
            ttfb_ms=ttfb_ms,
            http_version=self.http_version,
            response_wire=bytes(payload),
        )

    async def close(self) -> None:
        """Dispose of the shared HTTP client and its pooled connections."""
        await self.client.aclose()


class BenchmarkRunner:
    """Coordinate preflight, warm-up, caching, and the measured phase."""

    def __init__(
        self,
        endpoint: ResolverEndpoint,
        domains: list[str],
        options: BenchmarkOptions,
        progress_callback: ProgressCallback | None = None,
    ):
        self.endpoint = endpoint
        self.domains = domains
        self.options = options
        self.progress_callback = progress_callback
        self.cache = ResponseCache(options.cache_enabled)
        self.doh_client = DoHClient(endpoint, options) if endpoint.transport == "DoH" else None
        self.resolved_target = endpoint.bootstrap_address
        self._doh_preflight_http_version: str | None = None
        self._dot_connection_setup_ms: float | None = None
        self._workers: list[object] = []

    def _progress(self, phase: str, current: int, total: int, detail: str) -> None:
        """Forward progress to the UI when a callback was provided."""
        if self.progress_callback is not None:
            self.progress_callback(phase, current, total, detail)

    async def _preflight(self) -> str | None:
        """Fail fast when the endpoint or transport cannot be established."""
        self._progress("preflight", 0, 1, "Transport preflight")

        try:
            if self.endpoint.transport == "Do53":
                self.resolved_target = _resolve_target_address(
                    self.endpoint.target,
                    53,
                    socket.SOCK_DGRAM,
                )
                response, _used_tcp = await dns.asyncquery.udp_with_fallback(
                    _build_query(".", "NS"),
                    self.resolved_target,
                    timeout=self.options.timeout_seconds,
                    port=53,
                )
                if response.rcode() != dns.rcode.NOERROR:
                    raise RuntimeError(dns.rcode.to_text(response.rcode()))
            elif self.endpoint.transport == "DoT":
                self.resolved_target = self.endpoint.bootstrap_address or _resolve_target_address(
                    self.endpoint.target,
                    853,
                    socket.SOCK_STREAM,
                )
                worker = DoTWorker(
                    ResolverEndpoint(
                        name=self.endpoint.name,
                        transport="DoT",
                        target=self.resolved_target,
                        tls_hostname=self.endpoint.tls_hostname or self.endpoint.target,
                    ),
                    self.options,
                )
                try:
                    measurement = await worker.query(".")
                    if not measurement.success:
                        raise RuntimeError(measurement.error or "preflight failed")
                finally:
                    if worker.connection_setup_ms is not None:
                        # Reuse the same setup value in the final summary.
                        self._dot_connection_setup_ms = worker.connection_setup_ms
                    await worker.close()
            else:
                assert self.doh_client is not None
                await self.doh_client.measure_connection_setup()
                measurement = await self.doh_client.query(".", "NS")
                if not measurement.success:
                    raise RuntimeError(measurement.error or "preflight failed")
                self._doh_preflight_http_version = measurement.http_version
        except Exception as error:
            return f"preflight failed: {_safe_error(error)}"

        return None

    async def _make_worker(self):
        """Create one worker for the measured phase."""
        if self.endpoint.transport == "Do53":
            return Do53Worker(
                ResolverEndpoint(
                    name=self.endpoint.name,
                    transport="Do53",
                    target=self.resolved_target or self.endpoint.target,
                ),
                self.options,
            )
        if self.endpoint.transport == "DoT":
            return DoTWorker(
                ResolverEndpoint(
                    name=self.endpoint.name,
                    transport="DoT",
                    target=self.resolved_target or self.endpoint.target,
                    tls_hostname=self.endpoint.tls_hostname or self.endpoint.target,
                ),
                self.options,
            )
        assert self.doh_client is not None
        return self.doh_client

    async def _ensure_workers(self) -> None:
        """Create the worker pool once so warm-up and measurement share the same transport state."""
        if self._workers:
            return
        worker_count = min(self.options.concurrency, max(len(self.domains), 1))
        self._workers = [await self._make_worker() for _ in range(worker_count)]

    async def _warm_connections(self) -> None:
        """Warm up TLS sessions and HTTP pools without contaminating measured metrics."""
        if self.options.warmup_queries <= 0 or not self.domains:
            return

        await self._ensure_workers()
        for index in range(self.options.warmup_queries):
            domain = self.domains[index % len(self.domains)]
            worker = self._workers[index % len(self._workers)]
            self._progress("warmup", index + 1, self.options.warmup_queries, domain)
            await worker.query(domain, self.options.query_type) if isinstance(worker, DoHClient) else await worker.query(domain)

    async def _prime_cache(self) -> None:
        """Populate the cache with one uncaptured pass so warm runs measure cache hits only."""
        if not self.options.cache_enabled:
            return

        await self._ensure_workers()
        worker_count = len(self._workers)
        queue: asyncio.Queue[str] = asyncio.Queue()
        for domain in self.domains:
            queue.put_nowait(domain)

        async def cache_worker(worker_index: int) -> None:
            """Prime the cache with network responses before the warm measurement."""
            worker = self._workers[worker_index]
            while True:
                try:
                    domain = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                self._progress("cache", worker_index + 1, worker_count, domain)
                measurement = await worker.query(domain, self.options.query_type) if isinstance(worker, DoHClient) else await worker.query(domain)
                if measurement.success and measurement.response_wire is not None:
                    await self.cache.put(
                        domain,
                        self.options.query_type,
                        dns.message.from_wire(measurement.response_wire),
                    )
                queue.task_done()

        await asyncio.gather(*(cache_worker(index) for index in range(worker_count)))

    async def _measure(self) -> list[QueryMeasurement]:
        """Run the measured phase with bounded concurrency."""
        await self._ensure_workers()
        worker_count = len(self._workers)
        queue: asyncio.Queue[tuple[int, str]] = asyncio.Queue()
        for index, domain in enumerate(self.domains):
            queue.put_nowait((index, domain))

        measurements: list[QueryMeasurement | None] = [None] * len(self.domains)

        async def measure_worker(worker_index: int) -> None:
            """Execute benchmarked queries while reusing the worker transport state."""
            worker = self._workers[worker_index]
            while True:
                try:
                    index, domain = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                self._progress("measure", index + 1, len(self.domains), domain)
                cached = await self.cache.get(domain, self.options.query_type)
                if cached is not None:
                    measurements[index] = cached
                    queue.task_done()
                    continue

                measurement = await worker.query(domain, self.options.query_type) if isinstance(worker, DoHClient) else await worker.query(domain)
                measurements[index] = measurement
                queue.task_done()

        await asyncio.gather(*(measure_worker(index) for index in range(worker_count)))
        return [measurement for measurement in measurements if measurement is not None]

    async def run(self) -> BenchmarkResult:
        """Execute the full benchmark lifecycle and return the structured result."""
        preflight_error = await self._preflight()
        if preflight_error:
            return BenchmarkResult(
                protocol=self.endpoint.transport,
                endpoint=self.endpoint.target,
                target=self.endpoint.target,
                cache_mode=self.options.cache_mode,
                warmup_queries=self.options.warmup_queries,
                concurrency=self.options.concurrency,
                first_query_latency_ms=None,
                average_latency_ms=None,
                p95_latency_ms=None,
                success_rate=0.0,
                successful_queries=0,
                total_queries=len(self.domains),
                connection_setup_ms=self._dot_connection_setup_ms or (self.doh_client.connection_setup_ms if self.doh_client else None),
                average_ttfb_ms=None,
                http_version=self._doh_preflight_http_version,
                resolved_target=self.resolved_target,
                error=preflight_error,
            )

        await self._warm_connections()
        await self._prime_cache()
        measurements = await self._measure()

        successful = [measurement for measurement in measurements if measurement.success and measurement.latency_ms is not None]
        if not successful:
            return BenchmarkResult(
                protocol=self.endpoint.transport,
                endpoint=self.endpoint.target,
                target=self.endpoint.target,
                cache_mode=self.options.cache_mode,
                warmup_queries=self.options.warmup_queries,
                concurrency=self.options.concurrency,
                first_query_latency_ms=None,
                average_latency_ms=None,
                p95_latency_ms=None,
                success_rate=0.0,
                successful_queries=0,
                total_queries=len(measurements),
                connection_setup_ms=self._dot_connection_setup_ms or (self.doh_client.connection_setup_ms if self.doh_client else None),
                average_ttfb_ms=None,
                http_version=self._doh_preflight_http_version,
                resolved_target=self.resolved_target,
                error="no successful responses",
                measurements=measurements,
            )

        latency_values = [measurement.latency_ms for measurement in successful if measurement.latency_ms is not None]
        ttfb_values = [measurement.ttfb_ms for measurement in successful if measurement.ttfb_ms is not None]
        http_version = next((measurement.http_version for measurement in successful if measurement.http_version), self._doh_preflight_http_version)

        result = BenchmarkResult(
            protocol=self.endpoint.transport,
            endpoint=self.endpoint.target,
            target=self.endpoint.target,
            cache_mode=self.options.cache_mode,
            warmup_queries=self.options.warmup_queries,
            concurrency=self.options.concurrency,
            first_query_latency_ms=next(
                (measurement.latency_ms for measurement in measurements if measurement.latency_ms is not None),
                None,
            ),
            average_latency_ms=statistics.fmean(latency_values),
            p95_latency_ms=_percentile_95(latency_values),
            success_rate=(len(successful) / len(measurements)) * 100.0,
            successful_queries=len(successful),
            total_queries=len(measurements),
            connection_setup_ms=self._dot_connection_setup_ms or (self.doh_client.connection_setup_ms if self.doh_client else None),
            average_ttfb_ms=statistics.fmean(ttfb_values) if ttfb_values else None,
            http_version=http_version,
            resolved_target=self.resolved_target,
            measurements=measurements,
        )
        return result

    async def close(self) -> None:
        """Dispose of any shared resources after the benchmark completes."""
        for worker in self._workers:
            if isinstance(worker, Do53Worker) or isinstance(worker, DoTWorker):
                await worker.close()
        if self.doh_client is not None:
            await self.doh_client.close()


async def run_benchmark(
    endpoint: ResolverEndpoint,
    domains: list[str],
    options: BenchmarkOptions,
    progress_callback: ProgressCallback | None = None,
) -> BenchmarkResult:
    """Async entry point used by the worker thread."""
    runner = BenchmarkRunner(endpoint, domains, options, progress_callback)
    try:
        return await runner.run()
    finally:
        await runner.close()


def run_benchmark_sync(
    endpoint: ResolverEndpoint,
    domains: list[str],
    options: BenchmarkOptions,
    progress_callback: ProgressCallback | None = None,
) -> BenchmarkResult:
    """Synchronous wrapper so the GTK code can call the benchmark from a thread."""
    return asyncio.run(run_benchmark(endpoint, domains, options, progress_callback))
