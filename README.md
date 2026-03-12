# Bin Label Maker

Desktop application for generating printable bin labels on Avery label sheets. Built for Brennan Industries.

## Download

**[Download the latest Windows .exe from Releases](https://github.com/Jwood1126-coder/Bin-Label-Maker/releases/latest)**

No installation required — just download and run.

## Features

- Generate printable PDF label sheets for Avery 5160, 5163, and 5164 templates
- Each label includes: Brennan Part Number, Customer Part Number, Description, Part Image, QR Code, and Logo
- Live preview of the full label sheet before exporting
- Save and load customer projects instantly via the built-in project manager
- QR codes auto-generated as URLs for each part number
- Catsy PIM integration for automatic part data lookup (API credentials required)
- Export to PDF for printing on standard US Letter paper

## Quick Start

1. Download `BinLabelMaker.exe` from [Releases](https://github.com/Jwood1126-coder/Bin-Label-Maker/releases/latest)
2. Run the .exe (no install needed)
3. Type a customer name in the project combo box
4. Click **+ Add** to add labels
5. Fill in the Brennan Part #, Customer Part #, and Description
6. Click **Export PDF** to generate the printable sheet
7. Click **Save** to save the project for later

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

The app includes a **Lookup in Catsy** button that can search for parts and auto-fill label data. Currently uses sample data. To connect to the live Catsy API:

1. Get your API URL and Bearer Token from your Catsy admin
2. Update `src/bootstrap.py` — swap `MockCatsyService()` with `LiveCatsyService(api_url, bearer_token)`
3. That's it — the lookup button will now hit the real API

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

### Release a new version
```bash
git tag v1.0
git push --tags
```
GitHub Actions will automatically build the `.exe` and publish it to [Releases](https://github.com/Jwood1126-coder/Bin-Label-Maker/releases).

## Tech Stack

- **Python 3** + **PySide6** (LGPL licensed)
- **ReportLab** for PDF generation
- **qrcode + Pillow** for QR codes
- **PyInstaller** for Windows packaging
