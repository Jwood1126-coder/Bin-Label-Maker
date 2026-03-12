# Bin Label Maker

Desktop application for generating printable bin labels on Avery label sheets. Built for Brennan Industries.

![Brennan Industries](assets/brennan_logo_full.png)

## Download

**[Download the latest Windows .exe from Releases](https://github.com/Jwood1126-coder/Bin-Label-Maker/releases/latest)**

No installation required — just download and run.

## Features

- Generate printable PDF label sheets for Avery 5160, 5163, and 5164 templates
- Each label includes: Brennan Part Number, Customer Part Number, Description, Part Image, QR Code, and Logo
- Live preview of the full label sheet with page navigation
- Save and load customer projects instantly via the built-in project manager
- QR codes auto-generated as URLs for each part number
- **Live Catsy PIM integration** — search 122k+ products and auto-fill label data
- **CSV/Excel import** — bulk import parts from spreadsheets
- **Bulk part search** — search and select multiple parts at once
- Brennan Industries branded UI with company logos
- Export to PDF for printing on standard US Letter paper

## Quick Start

1. Download `BinLabelMaker.exe` from [Releases](https://github.com/Jwood1126-coder/Bin-Label-Maker/releases/latest)
2. Run the .exe (no install needed)
3. Type a customer name in the project combo box
4. Click **+ Add** to add labels, or use **Search Parts** to find parts in Catsy
5. Fill in the Brennan Part #, Customer Part #, and Description
6. Click **Export PDF** (Ctrl+E) to generate the printable sheet
7. Click **Save** to save the project for later

## Adding Parts

There are several ways to add parts to your label sheet:

- **Manual entry** — Click **+ Add** and type in the part details
- **Catsy lookup** — Use the "Lookup in Catsy" button to search by part number and auto-fill fields
- **Bulk search** — Click **Search Parts** to search Catsy, select multiple results with checkboxes, and add them all at once
- **CSV/Excel import** — Click **Import CSV/Excel** or use File > Import Parts from CSV/Excel (Ctrl+I) to bulk import from a spreadsheet
- **Duplicate** — Select a label and click **Duplicate** to copy it
- **Fill Sheet** — Click **Fill Sheet** to fill remaining slots with copies of the selected label

## Customer Project Management

Projects are saved locally in your app data folder for instant access:
- **Save** — saves current labels under the project name
- **Load** — reload a previously saved customer project
- **Save As** — clone a project under a new name
- **Delete** — remove a project you no longer need
- **Import/Export** — share `.blm` template files with others via File menu

## Supported Avery Templates

| Template | Label Size | Labels/Sheet | Grid |
|----------|-----------|-------------|------|
| Avery 5160 | 1" x 2-5/8" | 30 | 3x10 |
| Avery 5163 | 2" x 4" | 10 | 2x5 |
| Avery 5164 | 3-1/3" x 4" | 6 | 2x3 |

## Catsy PIM Integration

The app connects to the live Catsy PIM API (v4) at startup. If the API is reachable, all part lookups and searches pull real data from Brennan's 122k+ product catalog. If the API is unavailable, it falls back to sample data automatically.

Features powered by Catsy:
- **Lookup in Catsy** button in the label editor — search by part number, auto-fill all fields
- **Search Parts** button — bulk search and select multiple parts with checkboxes
- Cross-reference part numbers from 18+ manufacturers (Parker, Swagelok, Aeroquip, etc.)
- Product images from Catsy's S3-hosted asset library

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New template |
| Ctrl+O | Import template file |
| Ctrl+I | Import CSV/Excel |
| Ctrl+E | Export PDF |
| Ctrl+Q | Quit |

## Development

### Requirements
- Python 3.10+
- Dependencies: `pip install -r requirements.txt`

### Run locally
```bash
python main.py
```

### Build Windows .exe
```bash
pip install pyinstaller
pyinstaller bin_label_maker.spec
```
Output: `dist/BinLabelMaker.exe`

### Release a new version
```bash
git tag v1.x
git push --tags
```
GitHub Actions automatically builds the `.exe` on Windows and publishes it to [Releases](https://github.com/Jwood1126-coder/Bin-Label-Maker/releases).

## Tech Stack

- **Python 3** + **PySide6** (LGPL licensed)
- **ReportLab** for PDF generation
- **qrcode + Pillow** for QR codes
- **requests** for Catsy API integration
- **openpyxl** for Excel file import
- **PyInstaller** for single-file Windows packaging
