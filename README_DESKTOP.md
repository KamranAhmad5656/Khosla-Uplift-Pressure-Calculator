# Khosla Hydraulic Foundation Designer

Standalone Windows desktop application for hydraulic structure foundation analysis using only Khosla's Method of Independent Variables.

The previous browser/web version has been removed. This project is now desktop-only.

## Run

Double-click:

```text
run_khosla_desktop.bat
```

If the app does not open, double-click:

```text
diagnose_desktop.bat
```

That script checks whether Python and Tkinter are available.

The launcher now performs requirement bootstrapping:

1. Looks for a bundled `python\python.exe` beside the app.
2. Looks for Python 3.10+ through `py`, `python`, `python3`, and common install folders.
3. Verifies that Tkinter is available.
4. If Python is missing and `winget` exists, tries to install Python 3.12 automatically.
5. If automatic install is not possible, opens the official Python download page.

or run from this folder:

```powershell
py src\khosla_desktop_app.py
```

If `py` is not available:

```powershell
python src\khosla_desktop_app.py
```

Python is not currently available on PATH in this Codex shell. Install Python 3.10 or newer for Windows and enable **Add python.exe to PATH**.

No third-party Python packages are required. The app uses the standard Tkinter GUI library included with normal Python for Windows installations.

## Deploy To Another Computer

Double-click:

```text
make_distribution.bat
```

It creates:

```text
dist\Khosla Hydraulic Foundation Designer
```

Copy that folder to another Windows computer. On that computer, double-click:

```text
run_khosla_desktop.bat
```

The launcher will check requirements first and try to install Python if needed.

## Included

- Khosla end-pile equations.
- Khosla intermediate-pile equations.
- E, C, and D pressure percentage calculation.
- Mutual interference correction.
- Floor thickness correction.
- Slope correction.
- Node-based floor thickness schedule with interpolation between nodes.
- Uplift head and uplift pressure.
- Required floor thickness.
- Exit gradient check.
- Editable 2D section canvas.
- Live 3D concept view with variable floor thickness and pile selection.
- Professional summary dashboard.
- Validation and design warnings panel.
- Results table.
- Step-by-step calculation report.
- Native menu bar.
- Save/load project as JSON.
- Export formatted results as XLSX.
- Export engineering report as PDF.

## Desktop files

- `src\khosla_desktop_app.py` main application source.
- `src\khosla_desktop_app.pyw` windowed launcher.
- `run_khosla_desktop.bat` double-click launcher.
- `diagnose_desktop.bat` startup diagnostic script.
- `make_distribution.bat` creates a clean deployable folder.
- `requirements.txt` documents that no pip packages are needed.
- `README_DESKTOP.md` this guide.
