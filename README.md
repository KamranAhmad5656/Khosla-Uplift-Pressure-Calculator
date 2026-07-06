# Khosla Hydraulic Foundation Designer

Khosla Hydraulic Foundation Designer is a desktop engineering tool for seepage, uplift pressure, exit-gradient, and floor-thickness checks of hydraulic structures founded on pervious soil. The software focuses on Khosla's Method of Independent Variables and is intended for civil engineering education, textbook example verification, and preliminary hydraulic foundation design studies.

## Main Features

- Khosla end-pile and intermediate-pile pressure calculations.
- E, D, and C pressure percentage reporting.
- Mutual interference correction.
- Floor-thickness correction using node-based floor thickness.
- Slope correction option.
- Uplift head and uplift pressure calculations.
- Required floor thickness and safety status checks.
- Exit-gradient calculation and piping safety check.
- Editable 2D hydraulic section view.
- Conceptual 3D structure view.
- Results table, step-by-step calculation report, XLSX export, and one-page PDF report export.

## Repository Structure

```text
Khosla-Uplift-Pressure-Calculator/
├── README.md
├── LICENSE.txt
├── CITATION.cff
├── requirements.txt
├── src/
│   ├── khosla_desktop_app.py
│   └── khosla_desktop_app.pyw
├── validation/
│   ├── VALIDATION_NOTES.md
│   ├── validation_cases.xlsx
│   └── exported_report.pdf
├── screenshots/
│   ├── fig1_main_interface.png
│   ├── fig2_2d_section.png
│   ├── fig3_3d_view.png
│   ├── fig4_results_table.png
│   └── fig5_exported_report.png
└── sample_inputs/
    └── khosla_design_example.json
```

## Requirements

- Windows 10 or newer is recommended.
- Python 3.10 or newer.
- Tkinter, included with the normal Python installer for Windows.

No third-party Python packages are required.

## Running the Software

From the repository root:

```powershell
py src\khosla_desktop_app.py
```

or double-click:

```text
run_khosla_desktop.bat
```

The batch launcher checks whether Python and Tkinter are available before starting the app.

## Validation Material

The `validation/` folder contains benchmark notes and exported example outputs used to check the implementation against textbook-style Khosla method examples. The supplied cases cover:

- a three-pile barrage floor,
- analytical uncorrected pressure percentages,
- a two-pile weir floor,
- a regulator floor-thickness and exit-gradient example.

## License

This project is released under the MIT License. See `LICENSE.txt`.

## Citation

If this software is used in academic work, cite it using the metadata in `CITATION.cff`.

