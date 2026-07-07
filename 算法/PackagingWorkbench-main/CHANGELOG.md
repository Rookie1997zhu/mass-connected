# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-05-27

First public release.

### Added
- FEFCO 0201 (Regular Slotted Container) parametric box
- FEFCO 0301 (Tray and Lid) two-piece parametric box
- FEFCO 0713 (Tuck-end carton) parametric carton
- 2D dieline generation with Cut / Crease / Perforation layers
- DXF export support (via FreeCAD's native importDXF)
- "Hello Box" demo command for quick testing
- Reusable `BaseBox` scripted-object base and `utils/die_lines` helpers
- 45 automated tests (run without a FreeCAD installation)

### Fixed
- FEFCO 0201 exploded flaps no longer overlap adjacent panels at the corners
  (flaps inset and recentred on their panel; the 2D dieline is unchanged)
