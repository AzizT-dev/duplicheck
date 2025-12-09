<<<<<<< HEAD
# duplicheck
Plugin QGIS pour la détection et la gestion des doublons dans les couches vectorielles
=======
# DupliCheck

**Interactive Duplicate Detection and Management for QGIS**

![QGIS](https://img.shields.io/badge/QGIS-3.22+-green.svg)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Version](https://img.shields.io/badge/Version-1.2.0-orange.svg)

## Overview

DupliCheck is a QGIS plugin for detecting and managing duplicate features in vector layers. Unlike native QGIS tools that automatically delete duplicates, DupliCheck presents results interactively, allowing you to make informed decisions about which features to keep or remove.

## Features

- **Geometric duplicate detection** - Exact match or with configurable tolerance
- **Attribute duplicate detection** - Single or multiple fields comparison
- **Group-based management** - Handles N duplicates, not just pairs
- **Interactive visualization** - Highlights on QGIS main canvas
- **Click to zoom** - Single-click for highlight, double-click for zoom
- **Configurable priority rules** - Date, completeness, area, FID-based
- **Confidence scoring** - For each duplicate group
- **Export reports** - CSV, Excel, GeoPackage formats
- **Snapshot/restore** - Safe operations with undo capability
- **Multi-language** - FR, ES, AR, RU, DE, IT, PT, ZH

## Installation

### From ZIP file

1. Download the latest release ZIP file
2. In QGIS: `Plugins` → `Manage and Install Plugins` → `Install from ZIP`
3. Select the downloaded ZIP file
4. Restart QGIS if needed

### Manual installation

1. Extract the ZIP to your QGIS plugins folder:
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Restart QGIS
3. Enable the plugin in `Plugins` → `Manage and Install Plugins`

## Usage

### Basic workflow

1. **Open DupliCheck** from the Vector menu or toolbar
2. **Select a layer** to analyze
3. **Choose detection type**:
   - Geometric: Finds features with identical or similar geometries
   - Attribute: Finds features with matching attribute values
4. **Configure options** (tolerance, fields to compare, etc.)
5. **Run Detection**
6. **Review results** in the Results tab
7. **Click on features** to highlight and zoom on the map
8. **Mark actions** (Keep/Remove) for each feature
9. **Apply actions** to delete marked features

### Interaction

| Action | Result |
|--------|--------|
| Click on feature | Highlight + zoom |
| Double-click feature | Closer zoom |
| Click on group | Highlight all features in group |
| Double-click group | Zoom to entire group |

## Requirements

- QGIS 3.22 or higher
- Python 3.9+

## Changelog

### 1.2.0 (2025)
- Renamed from KAT DupliCheck to DupliCheck
- Fixed zoom for point geometries
- Removed embedded MapPreview - uses QGIS main canvas
- Improved highlight and zoom behavior

### 1.1.1
- Fixed zoom not working for point features
- Removed deprecated QgsRectangle.setMinimal()

### 1.0.0
- Initial release

## License

GNU General Public License v3.0

## Author

Aziz TRAORE  
Email: aziz.explorer@gmail.com

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## Support

For bug reports and feature requests, please use the [GitHub Issues](https://github.com/kaborodev/duplicheck/issues).
>>>>>>> 1960b1d (Initial commit: DupliCheck v1.0.0)
