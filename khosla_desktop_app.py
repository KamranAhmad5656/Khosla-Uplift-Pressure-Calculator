"""
Khosla Hydraulic Foundation Designer

Standalone Windows desktop application using Python Tkinter.
Focused only on Khosla's Method of Independent Variables.

Run:
    python khosla_desktop_app.py
or:
    py khosla_desktop_app.py
"""

from __future__ import annotations

import json
import math
import zipfile
from dataclasses import asdict, dataclass, field, fields
from datetime import date
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Canvas, Menu, StringVar, Tk, Text, filedialog, messagebox
from tkinter import ttk
from xml.sax.saxutils import escape as xml_escape


APP_TITLE = "Khosla Hydraulic Foundation Designer"


SLOPE_FACTORS = {
    "1:1": 11.2,
    "2:1": 6.5,
    "3:1": 4.5,
    "4:1": 3.3,
    "5:1": 2.8,
    "6:1": 2.5,
    "7:1": 2.3,
    "8:1": 2.0,
}


FLOOR_MATERIALS = {
    "Plain concrete": {"G": 2.40, "color": "#d9dee7"},
    "RCC": {"G": 2.50, "color": "#cbd5e1"},
    "Stone masonry": {"G": 2.65, "color": "#d6d3d1"},
    "Brick masonry": {"G": 1.90, "color": "#fca5a5"},
}


PILE_MATERIALS = {
    "Steel sheet pile": "#dc2626",
    "RCC cutoff": "#7c3aed",
    "Masonry cutoff": "#a16207",
    "Timber pile": "#92400e",
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def number(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return parsed


def fmt(value: float, digits: int = 3) -> str:
    if value is None or not math.isfinite(value):
        return "-"
    return f"{value:.{digits}f}"


@dataclass
class Pile:
    name: str
    x: float
    depth: float
    thickness: float
    material: str = "Steel sheet pile"


@dataclass
class FloorNode:
    name: str
    x: float
    thickness: float


@dataclass
class ProjectData:
    project_name: str = "Khosla Design Example"
    structure_type: str = "Barrage / Weir Floor"
    designer: str = ""
    design_date: str = field(default_factory=lambda: date.today().isoformat())
    pond_level: float = 105.0
    tail_water_level: float = 100.0
    upstream_bed_level: float = 99.0
    downstream_bed_level: float = 98.5
    floor_level: float = 99.0
    crest_level: float = 102.0
    floor_length: float = 72.0
    upstream_floor_to_crest: float = 18.0
    crest_width: float = 8.0
    downstream_glacis_length: float = 24.0
    slope_ratio: str = "4:1"
    floor_material: str = "Plain concrete"
    specific_gravity: float = 2.40
    unit_weight_water: float = 9.81
    safe_exit_gradient: float = 0.1667
    fos_uplift: float = 1.0
    apply_mutual_correction: bool = True
    apply_thickness_correction: bool = True
    apply_slope_correction: bool = True
    correction_mode: str = "Textbook selective"
    piles: list[Pile] = field(default_factory=lambda: [
        Pile("Pile 1", 0.0, 5.0, 1.5),
        Pile("Pile 2", 42.0, 6.0, 2.0),
        Pile("Pile 3", 72.0, 4.0, 1.8),
    ])
    floor_nodes: list[FloorNode] = field(default_factory=lambda: [
        FloorNode("N1", 0.0, 3.0),
        FloorNode("N2", 42.0, 4.0),
        FloorNode("N3", 72.0, 2.0),
    ])

    def sorted_floor_nodes(self) -> list[FloorNode]:
        return sorted(self.floor_nodes, key=lambda node: node.x)

    def floor_thickness_at(self, x_value: float) -> float:
        nodes = self.sorted_floor_nodes()
        if not nodes:
            return 0.0
        if x_value <= nodes[0].x:
            return max(nodes[0].thickness, 0.0)
        for index in range(1, len(nodes)):
            left = nodes[index - 1]
            right = nodes[index]
            if x_value <= right.x:
                span = max(right.x - left.x, 0.001)
                ratio = (x_value - left.x) / span
                return max(left.thickness + ratio * (right.thickness - left.thickness), 0.0)
        return max(nodes[-1].thickness, 0.0)


@dataclass
class ResultRow:
    pile_index: int
    pile: str
    point: str
    pile_type: str
    x: float
    depth: float
    thickness: float
    alpha: float
    alpha2: float | None
    lam: float
    base_phi: float
    mutual: float
    thickness_correction: float
    slope: float
    corrected_phi: float
    uplift_head: float
    uplift_pressure: float
    required_thickness: float
    safe: bool


def xml_clean(value: object) -> str:
    text = "" if value is None else str(value)
    return "".join(ch for ch in text if ch in "\t\n\r" or ord(ch) >= 32)


class SimpleXLSXWorkbook:
    """Small dependency-free XLSX writer for one formatted worksheet."""

    def __init__(self, sheet_name: str = "Khosla Results"):
        self.sheet_name = sheet_name[:31]
        self.rows: list[tuple[list[object], int]] = []
        self.autofilter: tuple[int, int, int, int] | None = None

    def add_row(self, values: list[object], style: int = 0) -> None:
        self.rows.append((values, style))

    @staticmethod
    def cell_ref(row: int, col: int) -> str:
        label = ""
        while col:
            col, rem = divmod(col - 1, 26)
            label = chr(65 + rem) + label
        return f"{label}{row}"

    def set_autofilter(self, first_row: int, first_col: int, last_row: int, last_col: int) -> None:
        self.autofilter = (first_row, first_col, last_row, last_col)

    def _content_types(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

    def _root_rels(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    def _workbook(self) -> str:
        name = xml_escape(xml_clean(self.sheet_name))
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="{name}" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

    def _workbook_rels(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    def _styles(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="3">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="14"/><name val="Calibri"/></font>
<font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font>
</fonts>
<fills count="6">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF70AD47"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFE2F0D9"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFE699"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFF4CCCC"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border><left style="thin"><color rgb="FF70AD47"/></left><right style="thin"><color rgb="FF70AD47"/></right><top style="thin"><color rgb="FF70AD47"/></top><bottom style="thin"><color rgb="FF70AD47"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="7">
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center"/></xf>
<xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="0" fillId="5" borderId="1" xfId="0" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""

    def _sheet(self) -> str:
        max_cols = max((len(row) for row, _style in self.rows), default=1)
        max_rows = max(len(self.rows), 1)
        dimension = f"A1:{self.cell_ref(max_rows, max_cols)}"
        cols = ["<cols>"]
        for col in range(1, max_cols + 1):
            cols.append(f'<col min="{col}" max="{col}" width="18" customWidth="1"/>')
        cols.append("</cols>")
        sheet_rows: list[str] = []
        for row_index, (values, row_style) in enumerate(self.rows, start=1):
            cells: list[str] = []
            for col_index, value in enumerate(values, start=1):
                ref = self.cell_ref(row_index, col_index)
                style = row_style
                if isinstance(value, (int, float)) and math.isfinite(float(value)):
                    cells.append(f'<c r="{ref}" s="{style}"><v>{float(value):.10g}</v></c>')
                else:
                    text = xml_escape(xml_clean(value))
                    cells.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>{text}</t></is></c>')
            sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        autofilter = ""
        if self.autofilter:
            r1, c1, r2, c2 = self.autofilter
            autofilter = f'<autoFilter ref="{self.cell_ref(r1, c1)}:{self.cell_ref(r2, c2)}"/>'
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<dimension ref="{dimension}"/>
<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
{"".join(cols)}
<sheetData>{"".join(sheet_rows)}</sheetData>
{autofilter}
</worksheet>"""

    def save(self, path: str | Path) -> None:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types())
            archive.writestr("_rels/.rels", self._root_rels())
            archive.writestr("xl/workbook.xml", self._workbook())
            archive.writestr("xl/_rels/workbook.xml.rels", self._workbook_rels())
            archive.writestr("xl/styles.xml", self._styles())
            archive.writestr("xl/worksheets/sheet1.xml", self._sheet())


class SimplePDFReport:
    """Minimal text PDF writer; enough for clean engineering reports without packages."""

    def __init__(self, title: str):
        self.title = title
        self.pages: list[list[str]] = []

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    @staticmethod
    def _wrap(line: str, width: int = 96) -> list[str]:
        if len(line) <= width:
            return [line]
        words = line.split()
        wrapped: list[str] = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 > width:
                wrapped.append(current)
                current = word
            else:
                current = word if not current else f"{current} {word}"
        if current:
            wrapped.append(current)
        return wrapped or [line[:width]]

    def set_text(self, text: str) -> None:
        lines: list[str] = []
        for raw in text.splitlines():
            if raw == "":
                lines.append("")
            else:
                lines.extend(self._wrap(raw))
        page: list[str] = []
        for line in lines:
            page.append(line)
            if len(page) >= 46:
                self.pages.append(page)
                page = []
        if page or not self.pages:
            self.pages.append(page)

    def save(self, path: str | Path) -> None:
        objects: list[bytes] = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(self.pages)))
        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>".encode("latin-1"))
        for index, page_lines in enumerate(self.pages):
            content_id = 4 + index * 2
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 {3 + len(self.pages) * 2} 0 R >> >> "
                f"/Contents {content_id} 0 R >>".encode("latin-1")
            )
            commands = ["BT", "/F1 10 Tf", "50 800 Td", "14 TL"]
            for line in page_lines:
                commands.append(f"({self._escape(line)}) Tj")
                commands.append("T*")
            commands.append("ET")
            stream = "\n".join(commands).encode("latin-1", errors="replace")
            objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for obj_id, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{obj_id} 0 obj\n".encode("latin-1"))
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref_start = len(output)
        output.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        output.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("latin-1")
        )
        Path(path).write_bytes(bytes(output))


class KhoslaEngine:
    def __init__(self, data: ProjectData):
        self.data = data

    @property
    def total_head(self) -> float:
        return max(self.data.pond_level - self.data.tail_water_level, 0.0)

    def sorted_piles(self) -> list[tuple[int, Pile]]:
        pairs = list(enumerate(self.data.piles))
        pairs.sort(key=lambda pair: pair[1].x)
        return pairs

    def end_pile_values(self, b: float, d: float) -> dict[str, float]:
        d = max(d, 0.001)
        alpha = b / d
        lam = (1.0 + math.sqrt(1.0 + alpha * alpha)) / 2.0
        phi_e = (100.0 / math.pi) * math.acos(clamp((lam - 2.0) / lam, -1.0, 1.0))
        phi_d = (100.0 / math.pi) * math.acos(clamp((lam - 1.0) / lam, -1.0, 1.0))
        return {"alpha": alpha, "lambda": lam, "phiE": phi_e, "phiD": phi_d}

    def intermediate_values(self, left: float, right: float, d: float) -> dict[str, float]:
        d = max(d, 0.001)
        alpha1 = max(left, 0.001) / d
        alpha2 = max(right, 0.001) / d
        root1 = math.sqrt(1.0 + alpha1 * alpha1)
        root2 = math.sqrt(1.0 + alpha2 * alpha2)
        lam = (root1 + root2) / 2.0
        lam1 = (root1 - root2) / 2.0
        phi_e = (100.0 / math.pi) * math.acos(clamp((lam1 - 1.0) / lam, -1.0, 1.0))
        phi_c = (100.0 / math.pi) * math.acos(clamp((lam1 + 1.0) / lam, -1.0, 1.0))
        phi_d = (100.0 / math.pi) * math.acos(clamp(lam1 / lam, -1.0, 1.0))
        return {
            "alpha": alpha1,
            "alpha2": alpha2,
            "lambda": lam,
            "lambda1": lam1,
            "phiE": phi_e,
            "phiC": phi_c,
            "phiD": phi_d,
        }

    def base_values_for_pile(self, sorted_index: int, pile: Pile, sorted_piles: list[tuple[int, Pile]]) -> dict[str, float | str | None]:
        b = max(self.data.floor_length, 0.001)
        if sorted_index == 0:
            values = self.end_pile_values(b, pile.depth)
            return {
                "type": "Upstream end pile",
                "alpha": values["alpha"],
                "alpha2": None,
                "lambda": values["lambda"],
                "E": 100.0,
                "C": 100.0 - values["phiE"],
                "D": 100.0 - values["phiD"],
            }
        if sorted_index == len(sorted_piles) - 1:
            values = self.end_pile_values(b, pile.depth)
            return {
                "type": "Downstream end pile",
                "alpha": values["alpha"],
                "alpha2": None,
                "lambda": values["lambda"],
                "E": values["phiE"],
                "C": 0.0,
                "D": values["phiD"],
            }
        values = self.intermediate_values(pile.x, b - pile.x, pile.depth)
        return {
            "type": "Intermediate pile",
            "alpha": values["alpha"],
            "alpha2": values["alpha2"],
            "lambda": values["lambda"],
            "E": values["phiE"],
            "C": values["phiC"],
            "D": values["phiD"],
        }

    def mutual_correction_value(self, influencing_depth: float, affected_depth: float, spacing: float) -> float:
        b = max(self.data.floor_length, 0.001)
        spacing = max(spacing, 0.001)
        influencing_depth = max(influencing_depth, 0.001)
        affected_depth = max(affected_depth, 0.001)
        return 19.0 * math.sqrt(influencing_depth / spacing) * ((affected_depth + influencing_depth) / b)

    def textbook_interfering_pile(
        self,
        sorted_index: int,
        point: str,
        sorted_piles: list[tuple[int, Pile]],
    ) -> tuple[Pile, float] | None:
        if point == "D" or len(sorted_piles) < 2:
            return None
        last = len(sorted_piles) - 1
        if sorted_index == 0 and point == "C":
            return sorted_piles[1][1], 1.0
        if 0 < sorted_index < last and point == "E":
            return sorted_piles[sorted_index - 1][1], -1.0
        if 0 < sorted_index < last and point == "C":
            return sorted_piles[sorted_index + 1][1], 1.0
        if sorted_index == last and point == "E":
            return sorted_piles[sorted_index - 1][1], -1.0
        return None

    def mutual_interference(
        self,
        sorted_index: int,
        pile: Pile,
        point: str,
        sorted_piles: list[tuple[int, Pile]],
    ) -> float:
        if not self.data.apply_mutual_correction or point == "D":
            return 0.0
        if self.data.correction_mode == "Textbook selective":
            match = self.textbook_interfering_pile(sorted_index, point, sorted_piles)
            if match is None:
                return 0.0
            other, sign = match
            spacing = abs(other.x - pile.x)
            return sign * self.mutual_correction_value(other.depth, pile.depth, spacing)
        total = 0.0
        for _, other in self.sorted_piles():
            if other is pile:
                continue
            spacing = max(abs(other.x - pile.x), 0.001)
            correction = self.mutual_correction_value(other.depth, pile.depth, spacing)
            sign = 1.0 if other.x < pile.x else -1.0
            total += sign * correction
        return total

    def floor_thickness_correction(
        self,
        sorted_index: int,
        base_phi: float,
        phi_d: float,
        pile: Pile,
        point: str,
        sorted_piles: list[tuple[int, Pile]],
    ) -> float:
        if not self.data.apply_thickness_correction or point == "D":
            return 0.0
        if self.data.correction_mode == "Textbook selective":
            last = len(sorted_piles) - 1
            allowed = (
                (sorted_index == 0 and point == "C")
                or (0 < sorted_index < last and point in {"E", "C"})
                or (sorted_index == last and point == "E")
            )
            if not allowed:
                return 0.0
        thickness = self.data.floor_thickness_at(pile.x)
        return ((phi_d - base_phi) / max(pile.depth, 0.001)) * thickness

    def slope_correction(self, sorted_index: int) -> float:
        if not self.data.apply_slope_correction or sorted_index == 0:
            return 0.0
        if self.data.correction_mode == "Textbook selective":
            return 0.0
        factor = SLOPE_FACTORS.get(self.data.slope_ratio, 0.0)
        return factor * self.data.downstream_glacis_length / max(self.data.floor_length, 0.001)

    def calculate(self) -> dict[str, object]:
        rows: list[ResultRow] = []
        sorted_piles = self.sorted_piles()
        h_total = self.total_head
        gamma_w = self.data.unit_weight_water
        g = self.data.specific_gravity
        for sorted_index, (original_index, pile) in enumerate(sorted_piles):
            pile.x = clamp(pile.x, 0.0, max(self.data.floor_length, 0.001))
            pile.depth = max(pile.depth, 0.001)
            base = self.base_values_for_pile(sorted_index, pile, sorted_piles)
            phi_d = float(base["D"])
            local_thickness = self.data.floor_thickness_at(pile.x)
            pile.thickness = local_thickness
            for point in ("E", "D", "C"):
                base_phi = float(base[point])
                mutual = self.mutual_interference(sorted_index, pile, point, sorted_piles)
                thick = self.floor_thickness_correction(sorted_index, base_phi, phi_d, pile, point, sorted_piles)
                slope = self.slope_correction(sorted_index)
                corrected_phi = clamp(base_phi + mutual + thick + slope, 0.0, 100.0)
                uplift_head = h_total * corrected_phi / 100.0
                uplift_pressure = gamma_w * uplift_head
                required_t = math.inf if g <= 1.0 else self.data.fos_uplift * uplift_head / (g - 1.0)
                rows.append(ResultRow(
                    pile_index=original_index,
                    pile=pile.name,
                    point=point,
                    pile_type=str(base["type"]),
                    x=pile.x,
                    depth=pile.depth,
                    thickness=local_thickness,
                    alpha=float(base["alpha"]),
                    alpha2=None if base["alpha2"] is None else float(base["alpha2"]),
                    lam=float(base["lambda"]),
                    base_phi=base_phi,
                    mutual=mutual,
                    thickness_correction=thick,
                    slope=slope,
                    corrected_phi=corrected_phi,
                    uplift_head=uplift_head,
                    uplift_pressure=uplift_pressure,
                    required_thickness=required_t,
                    safe=local_thickness >= required_t,
                ))

        downstream_pile = sorted_piles[-1][1]
        end = self.end_pile_values(max(self.data.floor_length, 0.001), downstream_pile.depth)
        exit_gradient = (h_total / max(downstream_pile.depth, 0.001)) * (1.0 / (math.pi * math.sqrt(end["lambda"])))
        exit_safe = exit_gradient <= self.data.safe_exit_gradient
        critical = max(rows, key=lambda row: row.uplift_head) if rows else None
        unsafe_count = sum(1 for row in rows if not row.safe)
        return {
            "rows": rows,
            "piles": sorted_piles,
            "H": h_total,
            "exit_gradient": exit_gradient,
            "exit_safe": exit_safe,
            "critical": critical,
            "unsafe_count": unsafe_count,
            "overall_safe": unsafe_count == 0 and exit_safe,
        }


class KhoslaDesktopApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1450x900")
        self.root.minsize(1180, 760)
        self.data = ProjectData()
        self.selected_pile_index: int | None = 0
        self.selected_node_index: int | None = 0
        self.drag: dict[str, object] | None = None
        self.hit_items: list[dict[str, object]] = []
        self.hit_items_3d: list[dict[str, object]] = []
        self.transform: dict[str, object] = {}
        self.transform_3d: dict[str, object] = {}
        self.drag_3d: dict[str, object] | None = None
        self.vars: dict[str, StringVar] = {}
        self.pile_vars: dict[str, StringVar] = {}
        self.node_vars: dict[str, StringVar] = {}
        self.validation_warnings: list[str] = []
        self.summary_vars = {
            "status": StringVar(value="-"),
            "head": StringVar(value="-"),
            "critical": StringVar(value="-"),
            "max_pressure": StringVar(value="-"),
            "exit_gradient": StringVar(value="-"),
            "unsafe": StringVar(value="-"),
            "required_t": StringVar(value="-"),
            "recommendation": StringVar(value="-"),
        }
        self.summary_labels: dict[str, ttk.Label] = {}
        self._resize_job: str | None = None
        self._configure_style()
        self._build_menu()
        self._build_ui()
        self.recalculate()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#f4f7fb")
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("TLabel", background="#f4f7fb", foreground="#102033")
        style.configure("Card.TLabel", background="#ffffff", foreground="#102033")
        style.configure("Header.TLabel", background="#f4f7fb", foreground="#102033", font=("Segoe UI", 17, "bold"))
        style.configure("Sub.TLabel", background="#f4f7fb", foreground="#64748b")
        style.configure("TButton", padding=(10, 6))
        style.configure("Danger.TButton", foreground="#dc2626")
        style.configure("Treeview", rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Summary.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("SummaryTitle.TLabel", background="#ffffff", foreground="#64748b", font=("Segoe UI", 8, "bold"))
        style.configure("SummaryValue.TLabel", background="#ffffff", foreground="#102033", font=("Segoe UI", 13, "bold"))
        style.configure("Safe.TLabel", background="#ffffff", foreground="#16a34a", font=("Segoe UI", 13, "bold"))
        style.configure("Unsafe.TLabel", background="#ffffff", foreground="#dc2626", font=("Segoe UI", 13, "bold"))
        style.configure("Warning.TLabel", background="#ffffff", foreground="#d97706", font=("Segoe UI", 13, "bold"))

    def _build_menu(self) -> None:
        menu = Menu(self.root)
        file_menu = Menu(menu, tearoff=0)
        file_menu.add_command(label="New Project", command=self.new_project)
        file_menu.add_command(label="Open Project JSON...", command=self.open_project)
        file_menu.add_command(label="Save Project JSON...", command=self.save_project)
        file_menu.add_separator()
        file_menu.add_command(label="Export Results XLSX...", command=self.export_xlsx)
        file_menu.add_command(label="Export Report PDF...", command=self.export_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menu.add_cascade(label="File", menu=file_menu)

        design_menu = Menu(menu, tearoff=0)
        design_menu.add_command(label="Recalculate", command=self.recalculate)
        design_menu.add_command(label="Add Pile", command=self.add_pile)
        design_menu.add_command(label="Delete Selected Pile", command=self.delete_selected_pile)
        menu.add_cascade(label="Design", menu=design_menu)

        help_menu = Menu(menu, tearoff=0)
        help_menu.add_command(label="Khosla Formula Reference", command=self.show_formula_reference)
        help_menu.add_command(label="About", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menu)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=BOTH, expand=True)

        header = ttk.Frame(main)
        header.pack(fill=X, pady=(0, 10))
        title_block = ttk.Frame(header)
        title_block.pack(side=LEFT)
        ttk.Label(title_block, text=APP_TITLE, style="Header.TLabel").pack(anchor="w")
        ttk.Label(title_block, text="Desktop Khosla method design assistant for hydraulic floors on pervious foundations.", style="Sub.TLabel").pack(anchor="w")
        self.status_var = StringVar(value="READY")
        ttk.Label(header, textvariable=self.status_var, style="Sub.TLabel").pack(side=RIGHT)

        toolbar = ttk.Frame(main)
        toolbar.pack(fill=X, pady=(0, 10))
        ttk.Button(toolbar, text="New", command=self.new_project).pack(side=LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Open JSON", command=self.open_project).pack(side=LEFT, padx=6)
        ttk.Button(toolbar, text="Save JSON", command=self.save_project).pack(side=LEFT, padx=6)
        ttk.Button(toolbar, text="Export XLSX", command=self.export_xlsx).pack(side=LEFT, padx=6)
        ttk.Button(toolbar, text="Export PDF", command=self.export_pdf).pack(side=LEFT, padx=6)
        ttk.Button(toolbar, text="Recalculate", command=self.recalculate).pack(side=LEFT, padx=6)

        body = ttk.PanedWindow(main, orient="horizontal")
        body.pack(fill=BOTH, expand=True)

        left = ttk.Frame(body, width=380)
        body.add(left, weight=0)
        right = ttk.Frame(body)
        body.add(right, weight=1)

        self._build_input_panel(left)
        self._build_workspace(right)

    def _build_input_panel(self, parent: ttk.Frame) -> None:
        canvas = Canvas(parent, bg="#f4f7fb", highlightthickness=0, width=390)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        content = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        self._install_mousewheel(canvas, content)

        self._section(content, "Project")
        self._entry(content, "Project name", "project_name")
        self._entry(content, "Structure type", "structure_type")
        self._entry(content, "Designer", "designer")
        self._entry(content, "Date", "design_date")

        self._section(content, "Water Levels / RL")
        self._entry(content, "Pond level", "pond_level")
        self._entry(content, "Tail water level", "tail_water_level")
        self._entry(content, "U/S bed level", "upstream_bed_level")
        self._entry(content, "D/S bed level", "downstream_bed_level")
        self._entry(content, "Floor level", "floor_level")
        self._entry(content, "Crest level", "crest_level")

        self._section(content, "Floor Geometry")
        self._entry(content, "Total floor length b", "floor_length")
        self._entry(content, "U/S floor to crest", "upstream_floor_to_crest")
        self._entry(content, "Crest width", "crest_width")
        self._entry(content, "D/S glacis length", "downstream_glacis_length")
        self._combo(content, "Slope ratio", "slope_ratio", list(SLOPE_FACTORS.keys()))

        self._section(content, "Floor Thickness Nodes")
        node_form = ttk.Frame(content, style="Card.TFrame", padding=10)
        node_form.pack(fill=X, pady=6)
        self._node_entry(node_form, "Node name", "name")
        self._node_entry(node_form, "x from U/S end", "x")
        self._node_entry(node_form, "Floor thickness t", "thickness")
        node_buttons = ttk.Frame(node_form, style="Card.TFrame")
        node_buttons.pack(fill=X, pady=(8, 0))
        ttk.Button(node_buttons, text="Add Node", command=self.add_floor_node).pack(side=LEFT, padx=(0, 6))
        ttk.Button(node_buttons, text="Update", command=self.update_selected_node).pack(side=LEFT, padx=6)
        ttk.Button(node_buttons, text="Delete", style="Danger.TButton", command=self.delete_selected_node).pack(side=LEFT, padx=6)

        node_columns = ("name", "x", "thickness")
        self.node_tree = ttk.Treeview(content, columns=node_columns, show="headings", height=5)
        for col, width in (("name", 90), ("x", 90), ("thickness", 120)):
            self.node_tree.heading(col, text=col)
            self.node_tree.column(col, width=width, anchor="center")
        self.node_tree.pack(fill=X, pady=(6, 12))
        self.node_tree.bind("<<TreeviewSelect>>", self.on_node_tree_select)

        self._section(content, "Material and Safety")
        self._combo(content, "Floor material", "floor_material", list(FLOOR_MATERIALS.keys()), self.apply_floor_material)
        self._entry(content, "Specific gravity G", "specific_gravity")
        self._entry(content, "Unit wt. water gamma_w", "unit_weight_water")
        self._entry(content, "Safe exit gradient", "safe_exit_gradient")
        self._entry(content, "FOS uplift", "fos_uplift")
        self._combo(content, "Correction mode", "correction_mode", ["Textbook selective", "Legacy all-pile"])
        self._check(content, "Mutual interference correction", "apply_mutual_correction")
        self._check(content, "Floor thickness correction", "apply_thickness_correction")
        self._check(content, "Slope correction", "apply_slope_correction")

        self._section(content, "Pile Editor")
        form = ttk.Frame(content, style="Card.TFrame", padding=10)
        form.pack(fill=X, pady=6)
        self._pile_entry(form, "Name", "name")
        self._pile_entry(form, "x from U/S end", "x")
        self._pile_entry(form, "Depth d", "depth")
        self._pile_combo(form, "Material", "material", list(PILE_MATERIALS.keys()))
        buttons = ttk.Frame(form, style="Card.TFrame")
        buttons.pack(fill=X, pady=(8, 0))
        ttk.Button(buttons, text="Add Pile", command=self.add_pile).pack(side=LEFT, padx=(0, 6))
        ttk.Button(buttons, text="Update", command=self.update_selected_pile).pack(side=LEFT, padx=6)
        ttk.Button(buttons, text="Delete", style="Danger.TButton", command=self.delete_selected_pile).pack(side=LEFT, padx=6)

        columns = ("name", "x", "depth", "floor_t", "material")
        self.pile_tree = ttk.Treeview(content, columns=columns, show="headings", height=8)
        for col, width in (("name", 80), ("x", 60), ("depth", 60), ("floor_t", 80), ("material", 120)):
            self.pile_tree.heading(col, text=col)
            self.pile_tree.column(col, width=width, anchor="center")
        self.pile_tree.pack(fill=X, pady=(6, 12))
        self.pile_tree.bind("<<TreeviewSelect>>", self.on_pile_tree_select)

    def _install_mousewheel(self, canvas: Canvas, content: ttk.Frame) -> None:
        def pointer_inside() -> bool:
            x = canvas.winfo_pointerx()
            y = canvas.winfo_pointery()
            root_x = canvas.winfo_rootx()
            root_y = canvas.winfo_rooty()
            return root_x <= x <= root_x + canvas.winfo_width() and root_y <= y <= root_y + canvas.winfo_height()

        def on_wheel(event) -> None:
            if not pointer_inside():
                return
            delta = -1 if event.delta > 0 else 1
            canvas.yview_scroll(delta * 3, "units")

        canvas.bind("<MouseWheel>", on_wheel)
        content.bind("<MouseWheel>", on_wheel)
        self.root.bind_all("<MouseWheel>", on_wheel, add="+")

    def _build_workspace(self, parent: ttk.Frame) -> None:
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=BOTH, expand=True)

        design_tab = ttk.Frame(self.notebook, padding=8)
        result_tab = ttk.Frame(self.notebook, padding=8)
        report_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(design_tab, text="Design Workspace")
        self.notebook.add(result_tab, text="Results")
        self.notebook.add(report_tab, text="Step-by-step Report")

        summary = ttk.Frame(design_tab)
        summary.pack(fill=X, pady=(0, 8))
        self._summary_card(summary, "Overall Status", "status", 0)
        self._summary_card(summary, "Seepage Head H", "head", 1)
        self._summary_card(summary, "Critical Point", "critical", 2)
        self._summary_card(summary, "Max Pressure", "max_pressure", 3)
        self._summary_card(summary, "Exit Gradient", "exit_gradient", 4)
        self._summary_card(summary, "Required Max t", "required_t", 5)
        self._summary_card(summary, "Unsafe Points", "unsafe", 6)
        self._summary_card(summary, "Recommendation", "recommendation", 7, wide=True)

        self.view_tabs = ttk.Notebook(design_tab)
        self.view_tabs.pack(fill=BOTH, expand=True)
        two_d_frame = ttk.Frame(self.view_tabs, padding=6)
        three_d_frame = ttk.Frame(self.view_tabs, padding=6)
        graph_frame = ttk.Frame(self.view_tabs, padding=6)
        self.view_tabs.add(two_d_frame, text="2D Section")
        self.view_tabs.add(three_d_frame, text="3D View")
        self.view_tabs.add(graph_frame, text="Pressure Graph")
        self.view_tabs.bind("<<NotebookTabChanged>>", self.schedule_redraw)

        ttk.Label(two_d_frame, text="Editable 2D Khosla Section", style="Sub.TLabel").pack(anchor="w")
        self.figure = Canvas(two_d_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#d9e4f0")
        self.figure.pack(fill=BOTH, expand=True, pady=(4, 0))
        self.figure.bind("<ButtonPress-1>", self.on_canvas_down)
        self.figure.bind("<B1-Motion>", self.on_canvas_drag)
        self.figure.bind("<ButtonRelease-1>", self.on_canvas_up)
        self.figure.bind("<Motion>", self.on_canvas_motion)

        ttk.Label(three_d_frame, text="Live 3D Concept View", style="Sub.TLabel").pack(anchor="w")
        self.view3d = Canvas(three_d_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#d9e4f0")
        self.view3d.pack(fill=BOTH, expand=True, pady=(4, 0))
        self.view3d.bind("<ButtonPress-1>", self.on_3d_down)
        self.view3d.bind("<B1-Motion>", self.on_3d_drag)
        self.view3d.bind("<ButtonRelease-1>", self.on_3d_up)
        self.view3d.bind("<Motion>", self.on_3d_motion)

        ttk.Label(graph_frame, text="Pressure Percentage Graph", style="Sub.TLabel").pack(anchor="w")
        self.graph = Canvas(graph_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#d9e4f0")
        self.graph.pack(fill=BOTH, expand=True, pady=(4, 0))

        columns = (
            "pile", "point", "type", "base", "mutual", "thick", "slope",
            "corrected", "head", "pressure", "req_t", "prov_t", "status",
        )
        result_split = ttk.PanedWindow(result_tab, orient="vertical")
        result_split.pack(fill=BOTH, expand=True)
        result_table_frame = ttk.Frame(result_split)
        warning_frame = ttk.Frame(result_split)
        result_split.add(result_table_frame, weight=4)
        result_split.add(warning_frame, weight=1)

        self.result_tree = ttk.Treeview(result_table_frame, columns=columns, show="headings")
        headings = {
            "pile": "Pile", "point": "Point", "type": "Type", "base": "Base %",
            "mutual": "Mutual", "thick": "t corr.", "slope": "Slope",
            "corrected": "Corrected %", "head": "h (m)", "pressure": "P kN/m2",
            "req_t": "Req t", "prov_t": "Prov t", "status": "Status",
        }
        for col in columns:
            self.result_tree.heading(col, text=headings[col])
            self.result_tree.column(col, width=95, anchor="center")
        self.result_tree.pack(fill=BOTH, expand=True)
        self.result_tree.tag_configure("unsafe", foreground="#dc2626")
        self.result_tree.tag_configure("safe", foreground="#166534")

        ttk.Label(warning_frame, text="Validation and Design Warnings", style="Sub.TLabel").pack(anchor="w")
        self.warning_text = Text(warning_frame, height=7, wrap="word", font=("Segoe UI", 9), bg="#fffaf0", fg="#713f12")
        self.warning_text.pack(fill=BOTH, expand=True, pady=(4, 0))

        self.report = Text(report_tab, wrap="word", font=("Consolas", 10), bg="#ffffff", fg="#102033")
        self.report.pack(fill=BOTH, expand=True)

        self.figure.bind("<Configure>", self.schedule_redraw)
        self.view3d.bind("<Configure>", self.schedule_redraw)
        self.graph.bind("<Configure>", self.schedule_redraw)

    def _section(self, parent: ttk.Frame, title: str) -> None:
        ttk.Label(parent, text=title, style="Header.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(12, 4))

    def _summary_card(self, parent: ttk.Frame, title: str, key: str, index: int, wide: bool = False) -> None:
        row = index // 4
        column = index % 4
        parent.columnconfigure(column, weight=1)
        card = ttk.Frame(parent, style="Summary.TFrame", padding=(10, 8))
        card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
        ttk.Label(card, text=title.upper(), style="SummaryTitle.TLabel").pack(anchor="w")
        wrap = 250 if wide else 160
        value = ttk.Label(card, textvariable=self.summary_vars[key], style="SummaryValue.TLabel", wraplength=wrap)
        value.pack(anchor="w", fill=X, pady=(2, 0))
        self.summary_labels[key] = value

    def show_formula_reference(self) -> None:
        messagebox.showinfo(
            "Khosla Formula Reference",
            "Khosla's Method of Independent Variables\n\n"
            "End pile:\n"
            "alpha = b / d\n"
            "lambda = (1 + sqrt(1 + alpha^2)) / 2\n"
            "phiE = (100/pi) cos^-1((lambda - 2) / lambda)\n"
            "phiD = (100/pi) cos^-1((lambda - 1) / lambda)\n\n"
            "Intermediate pile:\n"
            "alpha1 = b1 / d\n"
            "alpha2 = b2 / d\n"
            "lambda = [sqrt(1 + alpha1^2) + sqrt(1 + alpha2^2)] / 2\n"
            "lambda1 = [sqrt(1 + alpha1^2) - sqrt(1 + alpha2^2)] / 2\n\n"
            "Uplift:\n"
            "h = H * phi / 100\n"
            "P = gamma_w * h\n"
            "t = FOS * h / (G - 1)\n\n"
            "Exit gradient:\n"
            "GE = (H / d) * [1 / (pi * sqrt(lambda))]",
        )

    def show_about(self) -> None:
        messagebox.showinfo(
            APP_TITLE,
            "Professional desktop tool for Khosla uplift pressure analysis.\n\n"
            "This version is desktop-only and focused on Khosla's Method of Independent Variables.",
        )

    def _entry(self, parent: ttk.Frame, label: str, attr: str) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(8, 4))
        frame.pack(fill=X, pady=2)
        ttk.Label(frame, text=label, style="Card.TLabel").pack(anchor="w")
        value = getattr(self.data, attr)
        var = StringVar(value=str(value))
        self.vars[attr] = var
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(fill=X, pady=(3, 0))
        entry.bind("<FocusOut>", lambda _event: self.apply_inputs())
        entry.bind("<Return>", lambda _event: self.apply_inputs())

    def _combo(self, parent: ttk.Frame, label: str, attr: str, values: list[str], callback=None) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(8, 4))
        frame.pack(fill=X, pady=2)
        ttk.Label(frame, text=label, style="Card.TLabel").pack(anchor="w")
        var = StringVar(value=str(getattr(self.data, attr)))
        self.vars[attr] = var
        combo = ttk.Combobox(frame, textvariable=var, values=values, state="readonly")
        combo.pack(fill=X, pady=(3, 0))
        combo.bind("<<ComboboxSelected>>", lambda _event: callback() if callback else self.apply_inputs())

    def _check(self, parent: ttk.Frame, label: str, attr: str) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(8, 4))
        frame.pack(fill=X, pady=2)
        var = StringVar(value="1" if getattr(self.data, attr) else "0")
        self.vars[attr] = var
        check = ttk.Checkbutton(frame, text=label, variable=var, onvalue="1", offvalue="0", command=self.apply_inputs)
        check.pack(anchor="w")

    def _pile_entry(self, parent: ttk.Frame, label: str, key: str) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(fill=X, pady=2)
        ttk.Label(frame, text=label, style="Card.TLabel").pack(anchor="w")
        var = StringVar()
        self.pile_vars[key] = var
        ttk.Entry(frame, textvariable=var).pack(fill=X, pady=(3, 0))

    def _node_entry(self, parent: ttk.Frame, label: str, key: str) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(fill=X, pady=2)
        ttk.Label(frame, text=label, style="Card.TLabel").pack(anchor="w")
        var = StringVar()
        self.node_vars[key] = var
        ttk.Entry(frame, textvariable=var).pack(fill=X, pady=(3, 0))

    def _pile_combo(self, parent: ttk.Frame, label: str, key: str, values: list[str]) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(fill=X, pady=2)
        ttk.Label(frame, text=label, style="Card.TLabel").pack(anchor="w")
        var = StringVar(value=values[0])
        self.pile_vars[key] = var
        ttk.Combobox(frame, textvariable=var, values=values, state="readonly").pack(fill=X, pady=(3, 0))

    def apply_floor_material(self) -> None:
        name = self.vars["floor_material"].get()
        if name in FLOOR_MATERIALS:
            self.vars["specific_gravity"].set(str(FLOOR_MATERIALS[name]["G"]))
        self.apply_inputs()

    def apply_inputs(self) -> None:
        text_attrs = {"project_name", "structure_type", "designer", "design_date", "slope_ratio", "floor_material", "correction_mode"}
        bool_attrs = {"apply_mutual_correction", "apply_thickness_correction", "apply_slope_correction"}
        for attr, var in self.vars.items():
            if attr in text_attrs:
                setattr(self.data, attr, var.get())
            elif attr in bool_attrs:
                setattr(self.data, attr, var.get() == "1")
            else:
                setattr(self.data, attr, number(var.get(), getattr(self.data, attr)))
        self.validate_data()
        self.recalculate()

    def _validate_floor_nodes(self, warn) -> None:
        if not self.data.floor_nodes:
            self.data.floor_nodes = [
                FloorNode("N1", 0.0, max((pile.thickness for pile in self.data.piles), default=1.0)),
                FloorNode("N2", self.data.floor_length, max((pile.thickness for pile in self.data.piles), default=1.0)),
            ]
            warn("No floor thickness nodes existed. Default nodes were added at the start and end of the floor.")
        cleaned: list[FloorNode] = []
        seen: dict[float, FloorNode] = {}
        for node in self.data.floor_nodes:
            node.name = node.name or f"N{len(cleaned) + 1}"
            original_x = node.x
            node.x = clamp(number(node.x), 0.0, self.data.floor_length)
            if original_x != node.x:
                warn(f"{node.name} location was clamped within the floor length.")
            if number(node.thickness) <= 0:
                warn(f"{node.name} floor thickness must be positive. It has been limited to 0.001 m.")
            node.thickness = max(number(node.thickness), 0.001)
            key = round(node.x, 4)
            if key in seen:
                seen[key].thickness = node.thickness
                warn(f"Duplicate floor node at x = {fmt(node.x, 3)} m was merged.")
            else:
                seen[key] = node
                cleaned.append(node)
        cleaned.sort(key=lambda item: item.x)
        if abs(cleaned[0].x) > 0.001:
            cleaned.insert(0, FloorNode("N-start", 0.0, cleaned[0].thickness))
            warn("A start floor-thickness node was added at x = 0.")
        if abs(cleaned[-1].x - self.data.floor_length) > 0.001:
            cleaned.append(FloorNode("N-end", self.data.floor_length, cleaned[-1].thickness))
            warn("An end floor-thickness node was added at x = b.")
        self.data.floor_nodes = cleaned

    def validate_data(self) -> None:
        warnings: list[str] = []

        def warn(message: str) -> None:
            warnings.append(message)

        if self.data.pond_level <= self.data.tail_water_level:
            warn("Pond level should be higher than tail water level for upstream-to-downstream seepage. Calculation head H has been limited to zero.")
        if self.data.floor_length <= 0:
            warn("Floor length must be positive. It has been reset to 1.0 m.")
        self.data.floor_length = max(self.data.floor_length, 1.0)
        if self.data.specific_gravity <= 1.0:
            warn("Specific gravity G must be greater than 1. It has been limited to 1.01.")
        self.data.specific_gravity = max(self.data.specific_gravity, 1.01)
        if self.data.unit_weight_water <= 0:
            warn("Unit weight of water must be positive. It has been limited to 0.001.")
        self.data.unit_weight_water = max(self.data.unit_weight_water, 0.001)
        if self.data.safe_exit_gradient <= 0:
            warn("Safe exit gradient must be positive. It has been limited to 0.0001.")
        self.data.safe_exit_gradient = max(self.data.safe_exit_gradient, 0.0001)
        if self.data.fos_uplift <= 0:
            warn("FOS against uplift must be positive. It has been limited to 0.1.")
        self.data.fos_uplift = max(self.data.fos_uplift, 0.1)
        original_crest_start = self.data.upstream_floor_to_crest
        original_crest_width = self.data.crest_width
        original_ds_glacis = self.data.downstream_glacis_length
        self.data.upstream_floor_to_crest = clamp(self.data.upstream_floor_to_crest, 0.0, self.data.floor_length)
        self.data.crest_width = clamp(self.data.crest_width, 0.0, self.data.floor_length - self.data.upstream_floor_to_crest)
        self.data.downstream_glacis_length = clamp(
            self.data.downstream_glacis_length,
            0.0,
            self.data.floor_length - self.data.upstream_floor_to_crest - self.data.crest_width,
        )
        if (
            original_crest_start != self.data.upstream_floor_to_crest
            or original_crest_width != self.data.crest_width
            or original_ds_glacis != self.data.downstream_glacis_length
        ):
            warn("Glacis/crest geometry exceeded total floor length and was clamped within b.")
        self._validate_floor_nodes(warn)
        if not self.data.piles:
            warn("At least one pile is required. A default upstream pile has been added.")
            self.data.piles.append(Pile("Pile 1", 0.0, 5.0, 1.5))
        for pile in self.data.piles:
            original_x = pile.x
            pile.x = clamp(number(pile.x), 0.0, self.data.floor_length)
            if original_x != pile.x:
                warn(f"{pile.name} location was outside the floor and has been clamped to 0 <= x <= b.")
            if number(pile.depth) <= 0:
                warn(f"{pile.name} depth must be positive. It has been limited to 0.001 m.")
            pile.depth = max(number(pile.depth), 0.001)
            if pile.depth < 1.0:
                warn(f"{pile.name} depth is less than 1 m. Check exit gradient and cutoff adequacy.")
            pile.thickness = self.data.floor_thickness_at(pile.x)
            if pile.material not in PILE_MATERIALS:
                warn(f"{pile.name} had an unknown pile material and was reset to steel sheet pile.")
                pile.material = "Steel sheet pile"
        sorted_piles = sorted(self.data.piles, key=lambda item: item.x)
        for index in range(1, len(sorted_piles)):
            spacing = sorted_piles[index].x - sorted_piles[index - 1].x
            if abs(spacing) < 0.1:
                warn(f"{sorted_piles[index - 1].name} and {sorted_piles[index].name} are nearly at the same location. Increase spacing or delete one pile.")
        if sorted_piles and abs(sorted_piles[-1].x - self.data.floor_length) > max(1.0, 0.05 * self.data.floor_length):
            warn("The last pile is treated as the downstream pile but is not near the downstream end of the floor.")
        self.validation_warnings = warnings

    def recalculate(self) -> None:
        self.validate_data()
        self.engine = KhoslaEngine(self.data)
        self.result = self.engine.calculate()
        self.sync_vars_from_data()
        self.refresh_node_table()
        self.refresh_selected_node_form()
        self.refresh_pile_table()
        self.refresh_selected_pile_form()
        self.refresh_result_table()
        self.refresh_summary()
        self.refresh_warnings()
        self.draw_all()
        self.refresh_report()
        self.status_var.set(self.status_text())

    def status_text(self) -> str:
        result = self.result
        status = self.design_status()
        critical = result["critical"]
        critical_text = "-" if critical is None else f"{critical.pile} {critical.point}"
        return f"{status} | H = {fmt(result['H'])} m | Exit gradient = {fmt(result['exit_gradient'], 5)} | Critical = {critical_text}"

    def design_status(self) -> str:
        if not self.result["overall_safe"]:
            return "UNSAFE"
        if self.validation_warnings:
            return "WARNING"
        return "SAFE"

    def refresh_summary(self) -> None:
        rows: list[ResultRow] = self.result["rows"]
        critical = self.result["critical"]
        max_pressure = max((row.uplift_pressure for row in rows), default=0.0)
        max_required_t = max((row.required_thickness for row in rows), default=0.0)
        status = self.design_status()
        self.summary_vars["status"].set(status)
        self.summary_vars["head"].set(f"{fmt(self.result['H'])} m")
        self.summary_vars["critical"].set("-" if critical is None else f"{critical.pile} {critical.point}")
        self.summary_vars["max_pressure"].set(f"{fmt(max_pressure, 2)} kN/m2")
        self.summary_vars["exit_gradient"].set(f"{fmt(self.result['exit_gradient'], 5)}")
        self.summary_vars["unsafe"].set(str(self.result["unsafe_count"]))
        self.summary_vars["required_t"].set(f"{fmt(max_required_t, 3)} m")
        self.summary_vars["recommendation"].set(self.primary_recommendation())
        if "status" in self.summary_labels:
            status_style = "Safe.TLabel" if status == "SAFE" else "Warning.TLabel" if status == "WARNING" else "Unsafe.TLabel"
            self.summary_labels["status"].configure(style=status_style)
        if "exit_gradient" in self.summary_labels:
            self.summary_labels["exit_gradient"].configure(style="Safe.TLabel" if self.result["exit_safe"] else "Unsafe.TLabel")

    def primary_recommendation(self) -> str:
        if self.result["overall_safe"] and not self.validation_warnings:
            return "No action required"
        if not self.result["exit_safe"]:
            return "Increase downstream pile depth or floor length"
        unsafe_rows = [row for row in self.result["rows"] if not row.safe]
        if unsafe_rows:
            worst = max(unsafe_rows, key=lambda row: row.required_thickness - row.thickness)
            increase = max(worst.required_thickness - worst.thickness, 0.0)
            return f"Increase {worst.pile} floor t by {fmt(increase, 2)} m"
        if self.validation_warnings:
            return "Resolve validation warnings"
        return "Review geometry"

    def refresh_warnings(self) -> None:
        if not hasattr(self, "warning_text"):
            return
        warnings = list(self.validation_warnings)
        if not self.result["exit_safe"]:
            warnings.append("Exit gradient exceeds the safe limit. Increase downstream pile depth, increase floor length, or add an intermediate cutoff.")
        for row in self.result["rows"]:
            if not row.safe:
                warnings.append(f"{row.pile} {row.point}: required floor thickness {fmt(row.required_thickness, 3)} m exceeds provided {fmt(row.thickness, 3)} m.")
        if not warnings:
            warnings.append("No validation warnings. Current design satisfies the implemented Khosla uplift and exit-gradient checks.")
        self.warning_text.delete("1.0", END)
        self.warning_text.insert("1.0", "\n".join(f"- {warning}" for warning in warnings))

    def refresh_node_table(self) -> None:
        if not hasattr(self, "node_tree"):
            return
        for item in self.node_tree.get_children():
            self.node_tree.delete(item)
        for index, node in enumerate(self.data.floor_nodes):
            self.node_tree.insert("", END, iid=str(index), values=(node.name, fmt(node.x, 2), fmt(node.thickness, 3)))
        if self.selected_node_index is not None and self.selected_node_index < len(self.data.floor_nodes):
            self.node_tree.selection_set(str(self.selected_node_index))

    def refresh_selected_node_form(self) -> None:
        if not self.node_vars:
            return
        if self.selected_node_index is None or self.selected_node_index >= len(self.data.floor_nodes):
            self.selected_node_index = 0 if self.data.floor_nodes else None
        if self.selected_node_index is None:
            return
        node = self.data.floor_nodes[self.selected_node_index]
        self.node_vars["name"].set(node.name)
        self.node_vars["x"].set(fmt(node.x, 2))
        self.node_vars["thickness"].set(fmt(node.thickness, 3))

    def on_node_tree_select(self, _event=None) -> None:
        selection = self.node_tree.selection()
        if not selection:
            return
        self.selected_node_index = int(selection[0])
        self.refresh_selected_node_form()
        self.draw_all()

    def add_floor_node(self) -> None:
        x_value = self.data.floor_length / 2.0
        thickness = self.data.floor_thickness_at(x_value) or 1.0
        self.data.floor_nodes.append(FloorNode(f"N{len(self.data.floor_nodes) + 1}", x_value, thickness))
        self.data.floor_nodes.sort(key=lambda item: item.x)
        self.selected_node_index = min(range(len(self.data.floor_nodes)), key=lambda i: abs(self.data.floor_nodes[i].x - x_value))
        self.recalculate()

    def update_selected_node(self) -> None:
        if self.selected_node_index is None or self.selected_node_index >= len(self.data.floor_nodes):
            return
        node = self.data.floor_nodes[self.selected_node_index]
        node.name = self.node_vars["name"].get() or node.name
        node.x = number(self.node_vars["x"].get(), node.x)
        node.thickness = number(self.node_vars["thickness"].get(), node.thickness)
        self.data.floor_nodes.sort(key=lambda item: item.x)
        self.selected_node_index = min(range(len(self.data.floor_nodes)), key=lambda i: abs(self.data.floor_nodes[i].x - node.x))
        self.recalculate()

    def delete_selected_node(self) -> None:
        if self.selected_node_index is None or len(self.data.floor_nodes) <= 2:
            messagebox.showwarning(APP_TITLE, "At least two floor thickness nodes are required.")
            return
        del self.data.floor_nodes[self.selected_node_index]
        self.selected_node_index = min(self.selected_node_index, len(self.data.floor_nodes) - 1)
        self.recalculate()

    def refresh_pile_table(self) -> None:
        for item in self.pile_tree.get_children():
            self.pile_tree.delete(item)
        for index, pile in enumerate(self.data.piles):
            iid = str(index)
            self.pile_tree.insert("", END, iid=iid, values=(
                pile.name, fmt(pile.x, 2), fmt(pile.depth, 2), fmt(self.data.floor_thickness_at(pile.x), 3), pile.material,
            ))
        if self.selected_pile_index is not None and self.selected_pile_index < len(self.data.piles):
            self.pile_tree.selection_set(str(self.selected_pile_index))

    def refresh_selected_pile_form(self) -> None:
        if self.selected_pile_index is None or self.selected_pile_index >= len(self.data.piles):
            self.selected_pile_index = 0 if self.data.piles else None
        if self.selected_pile_index is None:
            return
        pile = self.data.piles[self.selected_pile_index]
        self.pile_vars["name"].set(pile.name)
        self.pile_vars["x"].set(fmt(pile.x, 2))
        self.pile_vars["depth"].set(fmt(pile.depth, 2))
        self.pile_vars["material"].set(pile.material)

    def refresh_result_table(self) -> None:
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        for row in self.result["rows"]:
            self.result_tree.insert("", END, values=(
                row.pile,
                row.point,
                row.pile_type,
                fmt(row.base_phi, 2),
                fmt(row.mutual, 2),
                fmt(row.thickness_correction, 2),
                fmt(row.slope, 2),
                fmt(row.corrected_phi, 2),
                fmt(row.uplift_head, 3),
                fmt(row.uplift_pressure, 2),
                fmt(row.required_thickness, 3),
                fmt(row.thickness, 3),
                "SAFE" if row.safe else "UNSAFE",
            ), tags=("safe" if row.safe else "unsafe",))

    def on_pile_tree_select(self, _event=None) -> None:
        selection = self.pile_tree.selection()
        if not selection:
            return
        self.selected_pile_index = int(selection[0])
        self.refresh_selected_pile_form()
        self.draw_all()

    def add_pile(self) -> None:
        next_x = self.data.floor_length if not self.data.piles else clamp(self.data.piles[-1].x + 10.0, 0.0, self.data.floor_length)
        self.data.piles.append(Pile(f"Pile {len(self.data.piles) + 1}", next_x, 4.0, self.data.floor_thickness_at(next_x)))
        self.selected_pile_index = len(self.data.piles) - 1
        self.recalculate()

    def update_selected_pile(self) -> None:
        if self.selected_pile_index is None:
            return
        pile = self.data.piles[self.selected_pile_index]
        pile.name = self.pile_vars["name"].get() or pile.name
        pile.x = number(self.pile_vars["x"].get(), pile.x)
        pile.depth = number(self.pile_vars["depth"].get(), pile.depth)
        pile.thickness = self.data.floor_thickness_at(pile.x)
        pile.material = self.pile_vars["material"].get()
        self.recalculate()

    def delete_selected_pile(self) -> None:
        if self.selected_pile_index is None or len(self.data.piles) <= 1:
            messagebox.showwarning(APP_TITLE, "At least one pile is required.")
            return
        del self.data.piles[self.selected_pile_index]
        self.selected_pile_index = min(self.selected_pile_index, len(self.data.piles) - 1)
        self.recalculate()

    def profile_points(self) -> list[tuple[float, float]]:
        b = self.data.floor_length
        floor = self.data.floor_level
        crest = self.data.crest_level
        downstream = self.data.downstream_bed_level
        crest_start = clamp(self.data.upstream_floor_to_crest, 0.0, b)
        crest_end = clamp(crest_start + self.data.crest_width, crest_start, b)
        ramp_end = clamp(crest_start + min(max(self.data.crest_width * 0.4, 2.0), max(self.data.crest_width, 0.0)), crest_start, crest_end)
        ds_end = clamp(crest_end + self.data.downstream_glacis_length, crest_end, b)
        points: list[tuple[float, float]] = []

        def push(x_value: float, level: float) -> None:
            if points and abs(points[-1][0] - x_value) < 0.001 and abs(points[-1][1] - level) < 0.001:
                return
            points.append((x_value, level))

        push(0.0, floor)
        push(crest_start, floor)
        if crest_end > crest_start:
            push(ramp_end, crest)
            push(crest_end, crest)
        push(ds_end, downstream)
        push(b, downstream)
        return points

    def profile_level_at(self, x_value: float) -> float:
        points = sorted(self.profile_points())
        if x_value <= points[0][0]:
            return points[0][1]
        for index in range(1, len(points)):
            x1, y1 = points[index - 1]
            x2, y2 = points[index]
            if x_value <= x2:
                ratio = (x_value - x1) / max(x2 - x1, 0.001)
                return y1 + ratio * (y2 - y1)
        return points[-1][1]

    def floor_section_points(self) -> list[tuple[float, float, float]]:
        x_values = {0.0, self.data.floor_length}
        x_values.update(x for x, _level in self.profile_points())
        x_values.update(node.x for node in self.data.floor_nodes)
        x_values.update(pile.x for pile in self.data.piles)
        return [
            (x_value, self.profile_level_at(x_value), self.data.floor_thickness_at(x_value))
            for x_value in sorted(clamp(x, 0.0, self.data.floor_length) for x in x_values)
        ]

    def drawing_transform(self, canvas: Canvas) -> dict[str, object]:
        width = max(canvas.winfo_width(), 800)
        height = max(canvas.winfo_height(), 420)
        pad = {"left": 72, "right": 42, "top": 34, "bottom": 96}
        points = self.profile_points()
        min_profile = min(level for _, level in points)
        max_depth = max((pile.depth for pile in self.data.piles), default=1.0)
        max_thickness = max((node.thickness for node in self.data.floor_nodes), default=1.0)
        min_level = min(min_profile, self.data.upstream_bed_level, self.data.downstream_bed_level) - max_depth - max_thickness - 1.0
        max_level = max(self.data.pond_level, self.data.tail_water_level, self.data.crest_level, self.data.upstream_bed_level, self.data.downstream_bed_level) + 1.0
        plot_w = width - pad["left"] - pad["right"]
        plot_h = height - pad["top"] - pad["bottom"]

        def sx(x_value: float) -> float:
            return pad["left"] + (clamp(x_value, 0.0, self.data.floor_length) / max(self.data.floor_length, 0.001)) * plot_w

        def sy(level: float) -> float:
            return pad["top"] + ((max_level - level) / max(max_level - min_level, 0.001)) * plot_h

        def to_x(pixel_x: float) -> float:
            return ((pixel_x - pad["left"]) / max(plot_w, 1.0)) * self.data.floor_length

        def to_level(pixel_y: float) -> float:
            return max_level - ((pixel_y - pad["top"]) / max(plot_h, 1.0)) * (max_level - min_level)

        return {
            "width": width,
            "height": height,
            "pad": pad,
            "sx": sx,
            "sy": sy,
            "to_x": to_x,
            "to_level": to_level,
            "min_level": min_level,
            "max_level": max_level,
        }

    def draw_all(self) -> None:
        self.draw_2d()
        self.draw_3d()
        self.draw_graph()

    def schedule_redraw(self, _event=None) -> None:
        if not hasattr(self, "result"):
            return
        if self._resize_job is not None:
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.root.after(80, self._redraw_from_resize)

    def _redraw_from_resize(self) -> None:
        self._resize_job = None
        self.draw_all()

    def draw_2d(self) -> None:
        canvas = self.figure
        canvas.delete("all")
        t = self.drawing_transform(canvas)
        self.transform = t
        sx = t["sx"]
        sy = t["sy"]
        width = t["width"]
        height = t["height"]
        pad = t["pad"]
        self.hit_items = []

        canvas.create_rectangle(0, 0, width, height, fill="#f8fbff", outline="")
        self.draw_grid(canvas, t)

        crest_start = clamp(self.data.upstream_floor_to_crest, 0.0, self.data.floor_length)
        crest_end = clamp(crest_start + self.data.crest_width, crest_start, self.data.floor_length)
        ds_end = clamp(crest_end + self.data.downstream_glacis_length, crest_end, self.data.floor_length)
        pond_y = sy(self.data.pond_level)
        tail_y = sy(self.data.tail_water_level)

        self.water_polygon(canvas, [(sx(0), pond_y), (sx(crest_start), pond_y), (sx(crest_start), sy(self.profile_level_at(crest_start))), (sx(0), sy(self.profile_level_at(0)))])
        self.water_polygon(canvas, [(sx(ds_end), tail_y), (sx(self.data.floor_length), tail_y), (sx(self.data.floor_length), sy(self.profile_level_at(self.data.floor_length))), (sx(ds_end), sy(self.profile_level_at(ds_end)))])

        canvas.create_line(sx(0), pond_y, sx(crest_start), pond_y, fill="#0284c7", width=2, dash=(8, 5))
        canvas.create_line(sx(ds_end), tail_y, sx(self.data.floor_length), tail_y, fill="#0284c7", width=2, dash=(8, 5))
        self.hit_items.append({"kind": "level", "attr": "pond_level", "box": (sx(0), pond_y - 10, sx(crest_start), pond_y + 10)})
        self.hit_items.append({"kind": "level", "attr": "tail_water_level", "box": (sx(ds_end), tail_y - 10, sx(self.data.floor_length), tail_y + 10)})
        self.hit_items.append({"kind": "level", "attr": "crest_level", "box": (sx(crest_start), sy(self.data.crest_level) - 10, sx(crest_end), sy(self.data.crest_level) + 10)})

        canvas.create_line(sx(0), sy(self.data.upstream_bed_level), sx(crest_start), sy(self.data.upstream_bed_level), fill="#94a3b8", width=2)
        canvas.create_line(sx(ds_end), sy(self.data.downstream_bed_level), sx(self.data.floor_length), sy(self.data.downstream_bed_level), fill="#94a3b8", width=2)

        floor_section = self.floor_section_points()
        top = [(sx(x), sy(level)) for x, level, _thickness in floor_section]
        bottom = [(sx(x), sy(level - thickness)) for x, level, thickness in reversed(floor_section)]
        color = FLOOR_MATERIALS.get(self.data.floor_material, FLOOR_MATERIALS["Plain concrete"])["color"]
        canvas.create_polygon(*(top + bottom), fill=color, outline="#94a3b8")
        self.line_points(canvas, top, fill="#111827", width=4)

        for index, node in enumerate(self.data.floor_nodes):
            level = self.profile_level_at(node.x)
            x = sx(node.x)
            y_top = sy(level)
            y_bottom = sy(level - node.thickness)
            selected = index == self.selected_node_index
            line_color = "#7c3aed" if selected else "#94a3b8"
            canvas.create_line(x, y_top, x, y_bottom, fill=line_color, width=2, dash=(4, 4))
            canvas.create_rectangle(x - 5, y_bottom - 5, x + 5, y_bottom + 5, fill="#7c3aed" if selected else "#64748b", outline="")
            canvas.create_text(x + 8, y_bottom - 8, text=f"{node.name} t={fmt(node.thickness, 2)} m", anchor="w", fill="#334155", font=("Segoe UI", 8, "bold"))
            self.hit_items.append({"kind": "node_move", "index": index, "box": (x - 12, y_top - 12, x + 12, y_bottom + 12)})
            self.hit_items.append({"kind": "node_thickness", "index": index, "box": (x - 18, y_bottom - 18, x + 18, y_bottom + 18)})

        seepage = [(sx(0), sy(self.profile_level_at(0) - 0.3))]
        for pile in self.data.piles:
            seepage.append((sx(pile.x), sy(self.profile_level_at(pile.x) - pile.depth)))
        seepage.append((sx(self.data.floor_length), sy(self.profile_level_at(self.data.floor_length) - 0.3)))
        self.line_points(canvas, seepage, fill="#f59e0b", width=2, dash=(7, 5))
        canvas.create_text(sx(self.data.floor_length * 0.42), sy(self.profile_level_at(self.data.floor_length * 0.42) - 1.2), text="seepage path", fill="#92400e", font=("Segoe UI", 9, "bold"))

        rows_by_pile: dict[int, dict[str, ResultRow]] = {}
        for row in self.result["rows"]:
            rows_by_pile.setdefault(row.pile_index, {})[row.point] = row

        for index, pile in enumerate(self.data.piles):
            top_level = self.profile_level_at(pile.x)
            x = sx(pile.x)
            y_top = sy(top_level)
            y_bottom = sy(top_level - pile.depth)
            selected = index == self.selected_pile_index
            pile_color = PILE_MATERIALS.get(pile.material, "#dc2626")
            if selected:
                canvas.create_line(x, y_top, x, y_bottom, fill="#93c5fd", width=13)
            canvas.create_line(x, y_top, x, y_bottom, fill=pile_color, width=6)
            canvas.create_oval(x - 4, y_top - 4, x + 4, y_top + 4, fill=pile_color, outline="")
            canvas.create_oval(x - 5, y_bottom - 5, x + 5, y_bottom + 5, fill=pile_color, outline="")
            self.hit_items.append({"kind": "pile_move", "index": index, "box": (x - 16, min(y_top, y_bottom) - 8, x + 16, max(y_top, y_bottom) + 8)})
            self.hit_items.append({"kind": "pile_depth", "index": index, "box": (x - 18, y_bottom - 18, x + 18, y_bottom + 18)})
            local_t = self.data.floor_thickness_at(pile.x)
            canvas.create_text(x + 26, (y_top + y_bottom) / 2, text=f"d = {fmt(pile.depth, 2)} m", anchor="w", fill="#1d4ed8", font=("Segoe UI", 9, "bold"))
            canvas.create_text(x + 26, (y_top + y_bottom) / 2 + 16, text=f"floor t = {fmt(local_t, 2)} m", anchor="w", fill="#475569", font=("Segoe UI", 8, "bold"))
            canvas.create_text(x + 8, y_bottom + 16, text=pile.name, anchor="w", fill="#334155", font=("Segoe UI", 9, "bold"))
            pile_rows = rows_by_pile.get(index, {})
            side = 1 if x < width * 0.75 else -1
            self.point_label(canvas, x - 8, y_top, f"E {fmt(pile_rows.get('E').corrected_phi if pile_rows.get('E') else 0, 1)}%", "#2563eb", side, -42)
            self.point_label(canvas, x + 8, y_top, f"C {fmt(pile_rows.get('C').corrected_phi if pile_rows.get('C') else 0, 1)}%", "#0891b2", side, -22)
            self.point_label(canvas, x, y_bottom, f"D {fmt(pile_rows.get('D').corrected_phi if pile_rows.get('D') else 0, 1)}%", "#dc2626", side, 8)

        self.dimension_line(canvas, sx(0), sx(self.data.floor_length), height - 34, f"b = {fmt(self.data.floor_length, 2)} m")
        sorted_piles = sorted(self.data.piles, key=lambda p: p.x)
        for idx in range(1, len(sorted_piles)):
            y = height - 70 - ((idx - 1) % 2) * 22
            self.dimension_line(canvas, sx(sorted_piles[idx - 1].x), sx(sorted_piles[idx].x), y, f"b{idx} = {fmt(sorted_piles[idx].x - sorted_piles[idx - 1].x, 2)} m")

        self.box_label(canvas, sx(0) + 6, pond_y - 22, "Pond Level", "#075985")
        self.box_label(canvas, sx(ds_end) + 6, tail_y - 22, "Tail Water", "#075985")
        self.box_label(canvas, sx(crest_start) + 10, sy(self.data.crest_level) - 26, "Crest Level", "#334155")
        self.box_label(canvas, sx(0) + 6, sy(self.data.upstream_bed_level) + 8, "U/S BED", "#475569")
        self.box_label(canvas, sx(self.data.floor_length) - 72, sy(self.data.downstream_bed_level) - 24, "D/S BED", "#475569")
        canvas.create_text(16, 16, text="Click pile/node = select | Drag pile shaft = move | Drag pile tip = depth | Drag node square = floor thickness | Drag dashed level = edit RL", anchor="nw", fill="#64748b", font=("Segoe UI", 9, "bold"))

    def draw_grid(self, canvas: Canvas, t: dict[str, object]) -> None:
        pad = t["pad"]
        sy = t["sy"]
        min_level = float(t["min_level"])
        max_level = float(t["max_level"])
        width = float(t["width"])
        range_level = max(max_level - min_level, 1.0)
        step = 5.0 if range_level > 20.0 else 2.0 if range_level > 10.0 else 1.0
        level = math.ceil(min_level / step) * step
        while level <= max_level:
            y = sy(level)
            canvas.create_line(pad["left"], y, width - pad["right"], y, fill="#e2e8f0")
            canvas.create_text(8, y, text=f"{fmt(level, 1)} RL", anchor="w", fill="#64748b", font=("Segoe UI", 8))
            level += step

    def water_polygon(self, canvas: Canvas, points: list[tuple[float, float]]) -> None:
        canvas.create_polygon(*points, fill="#bae6fd", outline="#7dd3fc")

    def line_points(self, canvas: Canvas, points: list[tuple[float, float]], **options) -> None:
        if len(points) < 2:
            return
        flat: list[float] = []
        for x, y in points:
            flat.extend([x, y])
        canvas.create_line(*flat, **options)

    def dimension_line(self, canvas: Canvas, x1: float, x2: float, y: float, text: str) -> None:
        if abs(x2 - x1) < 10:
            return
        canvas.create_line(x1, y, x2, y, fill="#2563eb", width=2)
        canvas.create_line(x1, y, x1 + 9, y - 6, fill="#2563eb", width=2)
        canvas.create_line(x1, y, x1 + 9, y + 6, fill="#2563eb", width=2)
        canvas.create_line(x2, y, x2 - 9, y - 6, fill="#2563eb", width=2)
        canvas.create_line(x2, y, x2 - 9, y + 6, fill="#2563eb", width=2)
        canvas.create_text((x1 + x2) / 2, y - 14, text=text, fill="#1d4ed8", font=("Segoe UI", 9, "bold"))

    def point_label(self, canvas: Canvas, x: float, y: float, text: str, color: str, side: int, offset_y: float) -> None:
        canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline="")
        text_x = x + side * 18
        text_y = y + offset_y
        anchor = "w" if side > 0 else "e"
        canvas.create_line(x, y, text_x, text_y + 8, fill=color)
        canvas.create_text(text_x, text_y, text=text, anchor=anchor, fill=color, font=("Segoe UI", 9, "bold"))

    def box_label(self, canvas: Canvas, x: float, y: float, text: str, color: str) -> None:
        pad_x = 5
        width = max(54, len(text) * 7 + 10)
        canvas.create_rectangle(x, y, x + width, y + 18, fill="#ffffff", outline="#d9e4f0")
        canvas.create_text(x + pad_x, y + 9, text=text, anchor="w", fill=color, font=("Segoe UI", 9, "bold"))

    def draw_3d(self) -> None:
        canvas = self.view3d
        canvas.delete("all")
        self.hit_items_3d = []
        width = max(canvas.winfo_width(), 500)
        height = max(canvas.winfo_height(), 320)
        canvas.create_rectangle(0, 0, width, height, fill="#f8fbff", outline="")
        b = max(self.data.floor_length, 1.0)
        origin_x = 56.0
        origin_y = height - 70.0
        scale_x = (width - 150.0) / b
        depth = min(150.0, max(95.0, width * 0.16))
        scale_z = 16.0
        base_level = min(level for _, level in self.profile_points()) - max((pile.depth for pile in self.data.piles), default=1.0) - 1.0

        def project(x_value: float, y_value: float, level: float) -> tuple[float, float]:
            return (
                origin_x + x_value * scale_x + y_value * 0.55,
                origin_y - (level - base_level) * scale_z - y_value * 0.28,
            )

        self.transform_3d = {
            "to_x": lambda pixel_x: (pixel_x - origin_x) / max(scale_x, 0.001),
        }

        section = self.floor_section_points()
        profile = [(x, level) for x, level, _thickness in section]
        top_front = [project(x, 0.0, level) for x, level, _thickness in section]
        top_back = [project(x, depth, level) for x, level, _thickness in section]
        bottom_front = [project(x, 0.0, level - thickness) for x, level, thickness in section]
        bottom_back = [project(x, depth, level - thickness) for x, level, thickness in section]
        floor_color = FLOOR_MATERIALS.get(self.data.floor_material, FLOOR_MATERIALS["Plain concrete"])["color"]
        for index in range(1, len(section)):
            quad = [top_front[index - 1], top_front[index], top_back[index], top_back[index - 1]]
            canvas.create_polygon(*quad, fill=floor_color, outline="#94a3b8")
            front_face = [top_front[index - 1], top_front[index], bottom_front[index], bottom_front[index - 1]]
            back_face = [top_back[index - 1], top_back[index], bottom_back[index], bottom_back[index - 1]]
            canvas.create_polygon(*front_face, fill="#e2e8f0", outline="#94a3b8")
            canvas.create_polygon(*back_face, fill="#cbd5e1", outline="#94a3b8")

        tail_start = clamp(self.data.upstream_floor_to_crest + self.data.crest_width + self.data.downstream_glacis_length, 0.0, b)
        self.draw_3d_water(canvas, project, 0.0, self.data.upstream_floor_to_crest, self.data.pond_level, depth, "Pond water")
        self.draw_3d_water(canvas, project, tail_start, b, self.data.tail_water_level, depth, "Tail water")

        for index, pile in enumerate(self.data.piles):
            top_level = self.profile_level_at(pile.x)
            bottom = top_level - pile.depth
            front_top = project(pile.x, 0.0, top_level)
            back_top = project(pile.x, depth, top_level)
            front_bottom = project(pile.x, 0.0, bottom)
            back_bottom = project(pile.x, depth, bottom)
            color = PILE_MATERIALS.get(pile.material, "#dc2626")
            selected = index == self.selected_pile_index
            canvas.create_line(*front_top, *front_bottom, fill="#93c5fd" if selected else color, width=8 if selected else 5)
            canvas.create_line(*back_top, *back_bottom, fill="#93c5fd" if selected else color, width=8 if selected else 5)
            canvas.create_line(*front_bottom, *back_bottom, fill=color, width=2)
            canvas.create_text(back_top[0] + 8, back_top[1] - 8, text=pile.name, anchor="w", fill="#334155", font=("Segoe UI", 9, "bold"))
            min_x = min(front_top[0], back_top[0], front_bottom[0], back_bottom[0]) - 14
            max_x = max(front_top[0], back_top[0], front_bottom[0], back_bottom[0]) + 50
            min_y = min(front_top[1], back_top[1], front_bottom[1], back_bottom[1]) - 20
            max_y = max(front_top[1], back_top[1], front_bottom[1], back_bottom[1]) + 20
            self.hit_items_3d.append({"kind": "pile_move", "index": index, "box": (min_x, min_y, max_x, max_y)})

        seepage = [project(0.0, 0.0, self.profile_level_at(0.0) - 0.3)]
        for pile in self.data.piles:
            seepage.append(project(pile.x, depth * 0.5, self.profile_level_at(pile.x) - pile.depth))
        seepage.append(project(b, depth, self.profile_level_at(b) - 0.3))
        self.line_points(canvas, seepage, fill="#f59e0b", width=2, dash=(7, 5))
        canvas.create_text(16, 16, text="3D view: click pile to select, drag pile horizontally to edit x-location", anchor="nw", fill="#64748b", font=("Segoe UI", 9, "bold"))

    def draw_3d_water(self, canvas: Canvas, project, x1: float, x2: float, level: float, depth: float, text: str) -> None:
        if x2 <= x1:
            return
        top1 = project(x1, 0.0, level)
        top2 = project(x2, 0.0, level)
        top3 = project(x2, depth, level)
        top4 = project(x1, depth, level)
        canvas.create_polygon(top1, top2, top3, top4, fill="#bae6fd", outline="#0284c7")
        canvas.create_text(top1[0] + 8, top1[1] - 16, text=text, anchor="w", fill="#075985", font=("Segoe UI", 9, "bold"))

    def draw_graph(self) -> None:
        canvas = self.graph
        canvas.delete("all")
        width = max(canvas.winfo_width(), 800)
        height = max(canvas.winfo_height(), 220)
        canvas.create_rectangle(0, 0, width, height, fill="#ffffff", outline="")
        rows: list[ResultRow] = self.result["rows"]
        if not rows:
            return
        pad = 44
        max_phi = max(1.0, max(row.corrected_phi for row in rows))
        bar_w = max(16.0, (width - 2 * pad) / len(rows) - 6)
        canvas.create_text(pad, 18, text="Corrected pressure percentage at E, D, C points", anchor="w", fill="#102033", font=("Segoe UI", 10, "bold"))
        canvas.create_line(pad, height - pad, width - pad, height - pad, fill="#d9e4f0")
        colors = {"E": "#2563eb", "C": "#0891b2", "D": "#dc2626"}
        for index, row in enumerate(rows):
            x = pad + index * (bar_w + 6)
            bar_h = (row.corrected_phi / max_phi) * (height - 2 * pad - 16)
            y = height - pad - bar_h
            canvas.create_rectangle(x, y, x + bar_w, height - pad, fill=colors[row.point], outline="")
            canvas.create_text(x + bar_w / 2, y - 8, text=fmt(row.corrected_phi, 1), fill="#102033", font=("Segoe UI", 8))
            canvas.create_text(x + bar_w / 2, height - pad + 14, text=f"{row.pile.replace('Pile ', 'P')}{row.point}", fill="#334155", font=("Segoe UI", 8))

    def hit_test(self, event) -> dict[str, object] | None:
        x = event.x
        y = event.y
        for item in reversed(self.hit_items):
            x1, y1, x2, y2 = item["box"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                return item
        return None

    def on_canvas_motion(self, event) -> None:
        item = self.hit_test(event)
        cursor = "arrow"
        if item:
            cursor = "sb_h_double_arrow" if item["kind"] in {"pile_move", "node_move"} else "sb_v_double_arrow"
        self.figure.configure(cursor=cursor)

    def on_canvas_down(self, event) -> None:
        item = self.hit_test(event)
        if not item:
            self.drag = None
            return
        self.drag = item
        if item["kind"] in {"pile_move", "pile_depth"}:
            self.selected_pile_index = int(item["index"])
            self.refresh_pile_table()
            self.refresh_selected_pile_form()
            self.draw_all()
        if item["kind"] in {"node_move", "node_thickness"}:
            self.selected_node_index = int(item["index"])
            self.refresh_node_table()
            self.refresh_selected_node_form()
            self.draw_all()

    def on_canvas_drag(self, event) -> None:
        if not self.drag:
            return
        to_x = self.transform["to_x"]
        to_level = self.transform["to_level"]
        kind = self.drag["kind"]
        if kind in {"pile_move", "pile_depth"}:
            index = int(self.drag["index"])
            pile = self.data.piles[index]
            if kind == "pile_move":
                pile.x = clamp(to_x(event.x), 0.0, self.data.floor_length)
            else:
                top_level = self.profile_level_at(pile.x)
                pile.depth = clamp(top_level - to_level(event.y), 0.5, 30.0)
        elif kind in {"node_move", "node_thickness"}:
            index = int(self.drag["index"])
            node = self.data.floor_nodes[index]
            if kind == "node_move":
                node.x = clamp(to_x(event.x), 0.0, self.data.floor_length)
            else:
                top_level = self.profile_level_at(node.x)
                node.thickness = clamp(top_level - to_level(event.y), 0.05, 20.0)
        elif kind == "level":
            setattr(self.data, str(self.drag["attr"]), number(to_level(event.y)))
            self.sync_vars_from_data()
        self.recalculate()

    def on_canvas_up(self, _event) -> None:
        self.drag = None

    def hit_test_3d(self, event) -> dict[str, object] | None:
        x = event.x
        y = event.y
        for item in reversed(self.hit_items_3d):
            x1, y1, x2, y2 = item["box"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                return item
        return None

    def on_3d_motion(self, event) -> None:
        item = self.hit_test_3d(event)
        self.view3d.configure(cursor="sb_h_double_arrow" if item else "arrow")

    def on_3d_down(self, event) -> None:
        item = self.hit_test_3d(event)
        self.drag_3d = item
        if not item:
            return
        if item["kind"] == "pile_move":
            self.selected_pile_index = int(item["index"])
            self.refresh_pile_table()
            self.refresh_selected_pile_form()
            self.draw_all()

    def on_3d_drag(self, event) -> None:
        if not self.drag_3d or self.drag_3d["kind"] != "pile_move":
            return
        index = int(self.drag_3d["index"])
        pile = self.data.piles[index]
        to_x = self.transform_3d.get("to_x")
        if not callable(to_x):
            return
        pile.x = clamp(to_x(event.x), 0.0, self.data.floor_length)
        self.recalculate()

    def on_3d_up(self, _event) -> None:
        self.drag_3d = None

    def sync_vars_from_data(self) -> None:
        bool_attrs = {"apply_mutual_correction", "apply_thickness_correction", "apply_slope_correction"}
        for attr, var in self.vars.items():
            if hasattr(self.data, attr):
                value = getattr(self.data, attr)
                if attr in bool_attrs:
                    var.set("1" if value else "0")
                else:
                    var.set(str(value))

    def refresh_report(self) -> None:
        report = self.generate_report()
        self.report.delete("1.0", END)
        self.report.insert("1.0", report)

    def generate_report(self) -> str:
        result = self.result
        lines = [
            APP_TITLE,
            "=" * len(APP_TITLE),
            "",
            f"Project: {self.data.project_name}",
            f"Structure: {self.data.structure_type}",
            f"Designer: {self.data.designer}",
            f"Date: {self.data.design_date}",
            "",
            "Design basis",
            "------------",
            "Method: Khosla's Method of Independent Variables",
            "Assumed seepage direction: upstream to downstream",
            "Units: length in m, pressure in kN/m2",
            "",
            "Hydraulic data",
            "--------------",
            f"H = Pond level - Tail water level",
            f"H = {fmt(self.data.pond_level)} - {fmt(self.data.tail_water_level)} = {fmt(result['H'])} m",
            f"U/S bed RL = {fmt(self.data.upstream_bed_level)} m",
            f"D/S bed RL = {fmt(self.data.downstream_bed_level)} m",
            f"Floor RL = {fmt(self.data.floor_level)} m",
            f"Crest RL = {fmt(self.data.crest_level)} m",
            "",
            "Geometry",
            "--------",
            f"Total impervious floor length b = {fmt(self.data.floor_length)} m",
            f"U/S floor to crest = {fmt(self.data.upstream_floor_to_crest)} m",
            f"Crest width = {fmt(self.data.crest_width)} m",
            f"D/S glacis length = {fmt(self.data.downstream_glacis_length)} m",
            f"Slope correction ratio = {self.data.slope_ratio}",
            "",
            "Floor thickness nodes",
            "---------------------",
        ]
        for node in self.data.floor_nodes:
            lines.append(f"{node.name}: x = {fmt(node.x)} m, floor thickness t = {fmt(node.thickness)} m")
        lines.extend([
            "",
            "Pile schedule",
            "-------------",
        ])
        for pile in self.data.piles:
            lines.append(f"{pile.name}: x = {fmt(pile.x)} m, d = {fmt(pile.depth)} m, local floor t = {fmt(self.data.floor_thickness_at(pile.x))} m, material = {pile.material}")
        lines.extend([
            "",
            "Khosla equations used",
            "---------------------",
            "For pile at end:",
            "alpha = b / d",
            "lambda = (1 + sqrt(1 + alpha^2)) / 2",
            "phiE = (100/pi) cos^-1((lambda - 2) / lambda)",
            "phiD = (100/pi) cos^-1((lambda - 1) / lambda)",
            "",
            "Exit gradient:",
            "GE = (H / d) * [1 / (pi * sqrt(lambda))]",
            f"GE = {fmt(result['exit_gradient'], 6)}",
            f"Safe exit gradient = {fmt(self.data.safe_exit_gradient, 6)}",
            f"Exit status = {'SAFE' if result['exit_safe'] else 'UNSAFE'}",
            "",
            "Corrections",
            "-----------",
            f"Correction mode: {self.data.correction_mode}",
            f"Mutual interference correction: {'Applied' if self.data.apply_mutual_correction else 'Not applied'}",
            f"Floor thickness correction: {'Applied' if self.data.apply_thickness_correction else 'Not applied'}",
            f"Slope correction: {'Applied' if self.data.apply_slope_correction else 'Not applied'}",
            "",
            "Point calculations",
            "------------------",
        ])
        for row in result["rows"]:
            lines.extend([
                f"{row.pile} point {row.point}:",
                f"  base phi = {fmt(row.base_phi, 3)} %",
                f"  mutual correction = {fmt(row.mutual, 3)} %",
                f"  thickness correction = {fmt(row.thickness_correction, 3)} %",
                f"  slope correction = {fmt(row.slope, 3)} %",
                f"  corrected phi = {fmt(row.corrected_phi, 3)} %",
                f"  h = H * phi / 100 = {fmt(result['H'])} * {fmt(row.corrected_phi)} / 100 = {fmt(row.uplift_head)} m",
                f"  pressure = gamma_w * h = {fmt(self.data.unit_weight_water)} * {fmt(row.uplift_head)} = {fmt(row.uplift_pressure)} kN/m2",
                f"  required t = FOS * h / (G - 1) = {fmt(self.data.fos_uplift)} * {fmt(row.uplift_head)} / ({fmt(self.data.specific_gravity)} - 1) = {fmt(row.required_thickness)} m",
                f"  provided t = {fmt(row.thickness)} m",
                f"  status = {'SAFE' if row.safe else 'UNSAFE'}",
                "",
            ])
        critical = result["critical"]
        lines.extend([
            "Summary",
            "-------",
            f"Overall status = {self.design_status()}",
            f"Unsafe pressure points = {result['unsafe_count']}",
            f"Critical point = {'-' if critical is None else critical.pile + ' ' + critical.point}",
            f"Primary recommendation = {self.primary_recommendation()}",
        ])
        if self.validation_warnings:
            lines.extend([
                "",
                "Validation warnings",
                "-------------------",
            ])
            lines.extend(f"- {warning}" for warning in self.validation_warnings)
        if not result["overall_safe"]:
            lines.extend([
                "",
                "Recommendations",
                "---------------",
                "- Increase floor thickness where required thickness exceeds provided thickness.",
                "- Increase downstream pile depth if exit gradient is unsafe.",
                "- Increase floor length or add an intermediate pile if pressure distribution is poor.",
                "- Provide inverted filter at downstream exit if piping risk remains.",
            ])
        return "\n".join(lines)

    def generate_pdf_report(self) -> str:
        result = self.result
        rows: list[ResultRow] = result["rows"]
        critical = result["critical"]
        lines = [
            APP_TITLE,
            "=" * len(APP_TITLE),
            "",
            f"Project: {self.data.project_name}",
            f"Structure: {self.data.structure_type}",
            f"Designer: {self.data.designer}",
            f"Date: {self.data.design_date}",
            "",
            "Hydraulic input",
            "---------------",
            f"Pond level = {fmt(self.data.pond_level)} m",
            f"Tail water level = {fmt(self.data.tail_water_level)} m",
            f"Total seepage head H = {fmt(result['H'])} m",
            f"Safe exit gradient = {fmt(self.data.safe_exit_gradient, 6)}",
            "",
            "Geometry and thickness schedule",
            "-------------------------------",
            f"Total impervious floor length b = {fmt(self.data.floor_length)} m",
            f"Crest RL = {fmt(self.data.crest_level)} m",
            f"Floor RL = {fmt(self.data.floor_level)} m",
            f"D/S glacis length = {fmt(self.data.downstream_glacis_length)} m",
            "",
            "Floor nodes:",
        ]
        for node in self.data.floor_nodes:
            lines.append(f"  {node.name}: x = {fmt(node.x)} m, t = {fmt(node.thickness)} m")
        lines.extend(["", "Pile schedule:"])
        for pile in self.data.piles:
            lines.append(f"  {pile.name}: x = {fmt(pile.x)} m, d = {fmt(pile.depth)} m, local t = {fmt(self.data.floor_thickness_at(pile.x))} m")
        lines.extend([
            "",
            "Calculation results",
            "-------------------",
            "Pile | Point | Base phi % | Mutual % | Thickness % | Slope % | Corrected phi % | h m | P kN/m2 | Required t m | Provided t m | Status",
        ])
        for row in rows:
            lines.append(
                f"{row.pile} | {row.point} | {fmt(row.base_phi, 2)} | {fmt(row.mutual, 2)} | "
                f"{fmt(row.thickness_correction, 2)} | {fmt(row.slope, 2)} | {fmt(row.corrected_phi, 2)} | "
                f"{fmt(row.uplift_head, 3)} | {fmt(row.uplift_pressure, 2)} | {fmt(row.required_thickness, 3)} | "
                f"{fmt(row.thickness, 3)} | {'SAFE' if row.safe else 'UNSAFE'}"
            )
        lines.extend([
            "",
            "Exit gradient check",
            "-------------------",
            f"Calculated exit gradient GE = {fmt(result['exit_gradient'], 6)}",
            f"Allowable exit gradient = {fmt(self.data.safe_exit_gradient, 6)}",
            f"Exit-gradient status = {'SAFE' if result['exit_safe'] else 'UNSAFE'}",
            "",
            "Summary",
            "-------",
            f"Overall status = {self.design_status()}",
            f"Unsafe pressure points = {result['unsafe_count']}",
            f"Critical point = {'-' if critical is None else critical.pile + ' ' + critical.point}",
            f"Primary recommendation = {self.primary_recommendation()}",
        ])
        if self.validation_warnings:
            lines.extend(["", "Validation warnings", "-------------------"])
            lines.extend(f"- {warning}" for warning in self.validation_warnings)
        return "\n".join(lines)

    def new_project(self) -> None:
        self.data = ProjectData()
        self.selected_pile_index = 0
        self.selected_node_index = 0
        self.sync_vars_from_data()
        self.recalculate()

    def save_project(self) -> None:
        self.apply_inputs()
        path = filedialog.asksaveasfilename(
            title="Save Khosla project",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        try:
            payload = asdict(self.data)
            Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not save project:\n{exc}")
            return
        messagebox.showinfo(APP_TITLE, f"Project saved:\n{path}")

    def open_project(self) -> None:
        path = filedialog.askopenfilename(title="Open Khosla project", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            pile_fields = {item.name for item in fields(Pile)}
            node_fields = {item.name for item in fields(FloorNode)}
            project_fields = {item.name for item in fields(ProjectData)}
            piles_payload = payload.pop("piles", [])
            floor_nodes_payload = payload.pop("floor_nodes", [])
            piles = []
            for pile in piles_payload:
                if not isinstance(pile, dict):
                    continue
                filtered = {key: value for key, value in pile.items() if key in pile_fields}
                piles.append(Pile(
                    str(filtered.get("name", f"Pile {len(piles) + 1}")),
                    number(filtered.get("x", 0.0)),
                    number(filtered.get("depth", 1.0), 1.0),
                    number(filtered.get("thickness", 1.0), 1.0),
                    str(filtered.get("material", "Steel sheet pile")),
                ))
            floor_nodes = []
            for node in floor_nodes_payload:
                if not isinstance(node, dict):
                    continue
                filtered = {key: value for key, value in node.items() if key in node_fields}
                floor_nodes.append(FloorNode(
                    str(filtered.get("name", f"N{len(floor_nodes) + 1}")),
                    number(filtered.get("x", 0.0)),
                    number(filtered.get("thickness", 1.0), 1.0),
                ))
            filtered_payload = {key: value for key, value in payload.items() if key in project_fields}
            self.data = ProjectData(**filtered_payload)
            self.data.piles = piles or [Pile("Pile 1", 0.0, 5.0, 1.5)]
            if floor_nodes:
                self.data.floor_nodes = floor_nodes
            else:
                self.data.floor_nodes = [
                    FloorNode(pile.name.replace("Pile", "N"), pile.x, max(pile.thickness, 0.001))
                    for pile in self.data.piles
                ]
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            messagebox.showerror(APP_TITLE, f"Could not open project:\n{exc}")
            return
        self.selected_pile_index = 0
        self.selected_node_index = 0
        self.sync_vars_from_data()
        self.recalculate()

    def export_xlsx(self) -> None:
        self.apply_inputs()
        path = filedialog.asksaveasfilename(
            title="Export Khosla results",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if not path:
            return
        try:
            workbook = SimpleXLSXWorkbook("Khosla Results")
            workbook.add_row([APP_TITLE], 1)
            workbook.add_row(["Project", self.data.project_name, "Structure", self.data.structure_type], 0)
            workbook.add_row(["Designer", self.data.designer, "Date", self.data.design_date], 0)
            workbook.add_row(["Total seepage head H (m)", self.result["H"], "Correction mode", self.data.correction_mode], 0)
            workbook.add_row([], 0)
            workbook.add_row(["Floor Thickness Nodes"], 6)
            workbook.add_row(["Node", "x (m)", "Floor thickness t (m)"], 2)
            for node in self.data.floor_nodes:
                workbook.add_row([node.name, node.x, node.thickness], 0)
            workbook.add_row([], 0)
            workbook.add_row(["Pile Schedule"], 6)
            workbook.add_row(["Pile", "x (m)", "Depth d (m)", "Local floor t (m)", "Material"], 2)
            for pile in self.data.piles:
                workbook.add_row([pile.name, pile.x, pile.depth, self.data.floor_thickness_at(pile.x), pile.material], 0)
            workbook.add_row([], 0)
            workbook.add_row(["Results Table"], 6)
            header_row = len(workbook.rows) + 1
            headers = [
                "Pile", "Point", "Type", "x (m)", "d (m)", "Base phi (%)", "Mutual (%)",
                "Thickness corr. (%)", "Slope corr. (%)", "Corrected phi (%)", "Uplift h (m)",
                "Pressure (kN/m2)", "Required t (m)", "Provided t (m)", "Status",
            ]
            workbook.add_row(headers, 2)
            for row in self.result["rows"]:
                workbook.add_row([
                    row.pile,
                    row.point,
                    row.pile_type,
                    row.x,
                    row.depth,
                    row.base_phi,
                    row.mutual,
                    row.thickness_correction,
                    row.slope,
                    row.corrected_phi,
                    row.uplift_head,
                    row.uplift_pressure,
                    row.required_thickness,
                    row.thickness,
                    "SAFE" if row.safe else "UNSAFE",
                ], 3 if row.safe else 5)
            last_result_row = len(workbook.rows)
            workbook.set_autofilter(header_row, 1, last_result_row, len(headers))
            workbook.add_row([], 0)
            workbook.add_row(["Summary"], 6)
            critical = self.result["critical"]
            workbook.add_row(["Overall status", self.design_status()], 5 if self.design_status() == "UNSAFE" else 3)
            workbook.add_row(["Critical point", "-" if critical is None else f"{critical.pile} {critical.point}"], 0)
            workbook.add_row(["Exit gradient", self.result["exit_gradient"]], 0)
            workbook.add_row(["Exit gradient status", "SAFE" if self.result["exit_safe"] else "UNSAFE"], 3 if self.result["exit_safe"] else 5)
            workbook.add_row(["Unsafe pressure points", self.result["unsafe_count"]], 0)
            workbook.add_row(["Primary recommendation", self.primary_recommendation()], 0)
            workbook.save(path)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not export XLSX:\n{exc}")
            return
        messagebox.showinfo(APP_TITLE, f"XLSX exported:\n{path}")

    def export_pdf(self) -> None:
        self.apply_inputs()
        path = filedialog.asksaveasfilename(
            title="Export PDF report",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return
        try:
            pdf = SimplePDFReport(APP_TITLE)
            pdf.set_text(self.generate_pdf_report())
            pdf.save(path)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not export PDF:\n{exc}")
            return
        messagebox.showinfo(APP_TITLE, f"PDF exported:\n{path}")


def main() -> None:
    root = Tk()
    app = KhoslaDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
