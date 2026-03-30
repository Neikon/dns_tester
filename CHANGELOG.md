# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog, with the newest entries first.

## [Unreleased]

### Added
- Added fair DNS benchmarking for `Do53`, `DoT`, and `DoH` with warm-up, concurrency, structured metrics, and optional warm-cache mode.
- Added a ranked summary dialog for `Check All` results.
- Added persistent DNS entry management so removed bundled entries stay hidden and custom entries survive app restarts.
- Added structured DNS region metadata with reusable formatting helpers.

### Changed
- Moved benchmark settings to a dedicated preferences dialog.
- Improved the `Check All` results dialog so the summary remains visible while the ranking scrolls.
- Refactored bundled DNS metadata to use stable IDs and structured origin tags instead of hardcoded flag text in provider names.

### Fixed
- Fixed benchmark JSON export so raw DNS wire payloads no longer break serialization.

## [25.12.08] - 2025-12-08

### Added
- Added the initial roadmap and versioning policy for the application.
