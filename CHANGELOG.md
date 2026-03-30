# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog, with the newest entries first.

## [Unreleased]

### Changed
- Replaced the placeholder Quad9 sidebar icon with the favicon published by the Quad9 website.
- Expanded the bundled Quad9 catalog to ship its recommended Malware Blocking + DNSSEC profile across Do53, DoT, and DoH.
- Expanded the bundled AdGuard catalog to include the official Default, Non-filtering, and Family Protection profiles across Do53, DoT, and DoH.
- Updated the README screenshot to the current provider-browser UI and removed the outdated image asset.
- Added bundled provider icons to the sidebar while keeping a generic fallback icon for user-defined DNS providers.
- Replaced the placeholder ControlD sidebar icon with the favicon published on the ControlD website.
- Removed an unused provider icon subdirectory left behind during the sidebar icon work.
- Moved bundled provider logo source files into a dedicated `data/provider-icons` directory so they stay separate from the app's own icons.
- Removed the obsolete duplicate provider icon files from `data/icons` so the sidebar uses the new dedicated provider icon asset set only.
- Replaced the placeholder DNS4EU, FlashStart, Gcore, and Mullvad sidebar icons with the favicons published by their websites.
- Simplified provider icon selection so icon names are derived from the provider label instead of a repetitive manual map.
- Replaced the placeholder Google and Cloudflare sidebar icons with the favicons published by their websites.
- Replaced the placeholder NextDNS sidebar icon with the favicon published by its website and refreshed the AdGuard asset from the official AdGuard DNS favicon.

## [26.03.30.1745] - 2026-03-30

### Added
- Added fair DNS benchmarking for `Do53`, `DoT`, and `DoH` with warm-up, concurrency, structured metrics, and optional warm-cache mode.
- Added a ranked summary dialog for `Check All` results.
- Added persistent DNS entry management so removed bundled entries stay hidden and custom entries survive app restarts.
- Added structured DNS region metadata with reusable formatting helpers.

### Changed
- Moved benchmark settings to a dedicated preferences dialog.
- Improved the `Check All` results dialog so the summary remains visible while the ranking scrolls.
- Refactored bundled DNS metadata to use stable IDs and structured origin tags instead of hardcoded flag text in provider names.
- Updated the About dialog to read the latest release notes from the AppStream metainfo file.
- Ignored the local `.codex` workspace marker so it no longer shows up in repository status.
- Documented that completed Git work must be pushed automatically so branches do not remain local-only by accident.
- Reworked DNS browsing into a libadwaita 1.9 provider sidebar so each provider now reveals its profiles, and each profile expands into its transport variants.
- Updated custom DNS entry storage to persist provider and profile metadata and keep older flat entries readable.
- Raised the Flatpak runtime to GNOME 50 so the new libadwaita 1.9 sidebar widgets are available.
- Integrated the sidebar and content area more cleanly and moved `Check All` to a fixed footer at the bottom of the provider sidebar.
- Replaced the provider switcher sidebar with `AdwSidebar` so provider navigation uses the new libadwaita 1.9 sidebar API directly.
- Split provider navigation into `Bundled` and `Custom` sidebar sections so user-added DNS providers are easier to distinguish from the shipped catalog.
- Open the `Check All` results dialog immediately and update it live with progress so long benchmark runs no longer look like the app has stalled.
- Moved the `Check All` action from the sidebar footer into the header bar to keep provider navigation focused and free vertical space.
- Added a tooltip to the header-bar `Check All` button to clarify that it benchmarks every listed DNS transport.
- Removed an extra root container from the main window layout so the split view hierarchy stays simpler and easier to maintain.
- Reimplemented the provider browser around `AdwNavigationSplitView` and `AdwBreakpoint` so the sidebar now follows the responsive layout pattern from the libadwaita documentation.
- Moved the bulk benchmark action into the sidebar header and switched it to a compact icon button so it stays close to provider navigation.
- Updated the bulk benchmark icon to a clearer play-style symbol so the action reads more like “run all tests”.
- Removed region flags from provider titles in the sidebar so the navigation list stays cleaner while the detailed origin info remains in the content pane.
- Removed provider flags from the detail-page titles as well, leaving the region badges only in the dedicated origin line.

### Fixed
- Fixed benchmark JSON export so raw DNS wire payloads no longer break serialization.
- Fixed benchmark JSON copy on GTK4/Wayland by using the current clipboard API.

## [25.12.08] - 2025-12-08

### Added
- Added the initial roadmap and versioning policy for the application.
