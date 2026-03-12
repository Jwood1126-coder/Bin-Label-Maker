# Bin Label Maker - Development Guide

## Project Overview
Desktop application for Brennan Industries to generate printable bin labels on Avery label sheets.
Compiled to a single Windows `.exe` via PyInstaller. Users download from GitHub Releases.

## Build & Release Process
- **CI/CD**: GitHub Actions workflow at `.github/workflows/build.yml`
- **Trigger**: Push a git tag like `v1.x` to build and publish automatically
- **Output**: Single `BinLabelMaker.exe` attached to a GitHub Release
- **Download link**: https://github.com/Jwood1126-coder/Bin-Label-Maker/releases/latest
- Users should always be able to click that link and download the latest .exe. No install required.

### To release a new version:
```bash
git tag v1.x
git push --tags
```
GitHub Actions builds on `windows-latest` with Python 3.12, runs `pyinstaller bin_label_maker.spec`, and uploads the .exe to a new Release.

## Tech Stack
- **Python 3.12** + **PySide6** (LGPL - free distribution)
- **ReportLab** for PDF generation
- **qrcode + Pillow** for QR codes
- **requests** for Catsy API
- **openpyxl** for Excel import
- **PyInstaller** for Windows .exe packaging
- **JSON** for template save/load

## Architecture
- **MVP pattern**: Models / Views / Presenters
- **Constructor DI** via `src/bootstrap.py` (composition root)
- **Decoupled layout engine**: `label_layout.py` computes pure geometry, renderers consume it
- **Abstract DataSource**: interface in `data_source.py`, live Catsy client + mock fallback
- **Theme module**: `src/views/theme.py` has all Brennan brand colors, QSS stylesheet, asset paths

## Key File Map
```
main.py                          # Entry point, applies theme
src/bootstrap.py                 # DI wiring, Catsy API config
src/views/theme.py               # Brennan brand colors, stylesheet, asset paths
src/views/main_window.py         # Main window with branded header
src/views/label_editor.py        # Single label edit form
src/views/label_list_panel.py    # Label table with add/remove/dup/fill
src/views/preview_panel.py       # Live sheet preview with page nav
src/views/bulk_search_dialog.py  # Multi-part search dialog
src/views/avery_selector.py      # Avery template dropdown
src/models/avery_templates.py    # Avery geometry definitions (5160, 5163, 5164)
src/models/template.py           # Template dataclass (customer, labels, settings)
src/models/label_data.py         # LabelData dataclass
src/services/label_layout.py     # Pure geometry engine
src/services/pdf_renderer.py     # ReportLab PDF output
src/services/preview_renderer.py # QPixmap preview rendering
src/services/catsy_live.py       # Live Catsy v4 API client
src/services/catsy_mock.py       # Mock data fallback
src/services/csv_importer.py     # CSV/Excel import
src/services/qr_generator.py     # QR code generation
src/services/template_io.py      # JSON save/load
src/services/project_manager.py  # Local project storage
assets/                          # Brennan logos (PNG, SVG)
bin_label_maker.spec             # PyInstaller config
.github/workflows/build.yml      # CI/CD build pipeline
```

## Catsy PIM Integration (LIVE)
- **API Base**: `https://api.catsy.com/v4`
- **Auth**: Bearer Token in `src/bootstrap.py`
- **Search**: `POST /v4/products/filter` with `{attributeKey, operator, value}` filters
- **Rate limit**: 2 req/sec, burst 10, 429 handled with exponential backoff
- **122k+ products** in catalog
- Falls back to MockCatsyService if API is unreachable

## Brennan Brand Theme
- Primary Blue: `#006293`
- All UI styling in `src/views/theme.py`
- Logos in `assets/` directory (downloaded from brennaninc.com CDN)
- New templates auto-use Brennan logo via DI in bootstrap.py
- PyInstaller bundles assets directory into the .exe

## Conventions
- Never commit secrets to new files; API token is already in bootstrap.py by design
- Use `setProperty("cssClass", "secondary")` or `"danger"` for button variants
- Use `setObjectName()` for inline QSS scoping to avoid style leaks
- Presenters must not import from the views layer; use constructor DI instead
- All dependencies wired in bootstrap.py, nowhere else
