#!/usr/bin/env python3
"""Validate the Home Intelligence XLSX without third-party spreadsheet libraries."""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "docs/product/home-intelligence/requirements.xlsx"
ROADMAP = ROOT / "docs/product/home-intelligence/roadmap.yaml"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

MASTER_HEADERS = [
    "ID", "Parent ID", "Level", "Title", "Roadmap ID", "Roadmap", "Epic ID", "Epic",
    "Release", "Outcome", "User Story", "Description", "Acceptance Criteria", "Non-goal",
    "Priority", "Status", "Owner Role", "Story Points", "Dependencies", "Risk",
    "Architecture Ref", "UX Ref", "Verification", "Evidence Link", "Jira Default Type",
    "Jira Advanced Type", "GitHub Type", "Labels", "Source", "Updated At",
]
VIEW_HEADERS = {
    "Jira-Standard": ["Work item ID", "Work type", "Summary", "Description", "Parent", "Priority", "Labels", "Fix Version", "Story Points", "Logical ID", "Parent Logical ID", "Roadmap", "Status"],
    "Jira-Advanced": ["Work item ID", "Work type", "Summary", "Description", "Parent", "Priority", "Labels", "Fix Version", "Story Points", "Logical ID", "Parent Logical ID", "Status"],
    "GitHub": ["Title", "Body", "Type", "Parent Logical ID", "Logical ID", "Status", "Priority", "Milestone", "Labels", "Estimate", "Blocked By", "Evidence Link"],
}
LEVEL_PREFIX = {"ZW-RM-": "Roadmap", "ZW-EP-": "Epic", "ZW-ST-": "Story", "ZW-TK-": "Task"}
OWNER_ROLES = {"human", "planner", "generator", "evaluator", "product", "frontend", "platform", "agent", "security", "devops", "qa", "harness"}
STORY_OWNER_ROLES = OWNER_ROLES - {"harness"}
RISKS = {"Low", "Medium", "High"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
STATUSES = {"Draft", "Design & Test", "In Progress", "Review", "Ready to Merge", "Blocked", "Done", "Ready"}
RELEASE_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
KPI_ACCEPTANCE = {
    "ZW-ST-0301": ("95%", "心跳窗口"),
    "ZW-ST-0304": ("99%", "设备真实状态"),
    "ZW-ST-0501": ("80%", "两次交互"),
    "ZW-ST-1101": ("95%", "场景"),
    "ZW-ST-1503": ("100%", "高风险"),
    "ZW-ST-1703": ("100%", "发布变更"),
}


def column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref).group(0)
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value - 1


def read_workbook(path: Path) -> dict[str, list[list[object | None]]]:
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", NS):
                shared.append("".join(node.text or "" for node in item.iterfind(".//m:t", NS)))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("r:Relationship", REL_NS)}
        sheets: dict[str, list[list[object | None]]] = {}
        for sheet in workbook.findall("m:sheets/m:sheet", NS):
            name = sheet.attrib["name"]
            target = targets[sheet.attrib[RID]].replace("\\", "/")
            member = target.lstrip("/") if target.startswith("/xl/") else f"xl/{target.lstrip('/')}"
            xml = ET.fromstring(archive.read(member))
            rows: list[list[object | None]] = []
            for row in xml.findall("m:sheetData/m:row", NS):
                cells: dict[int, object | None] = {}
                for cell in row.findall("m:c", NS):
                    index = column_index(cell.attrib["r"])
                    kind = cell.attrib.get("t")
                    value_node = cell.find("m:v", NS)
                    if kind == "inlineStr":
                        value: object | None = "".join(node.text or "" for node in cell.iterfind(".//m:t", NS))
                    elif value_node is None:
                        value = None
                    elif kind == "s":
                        value = shared[int(value_node.text)]
                    elif kind in {"str", "e"}:
                        value = value_node.text
                    elif kind == "b":
                        value = value_node.text == "1"
                    else:
                        raw = value_node.text or ""
                        try:
                            number = float(raw)
                            value = int(number) if number.is_integer() else number
                        except ValueError:
                            value = raw
                    cells[index] = value
                width = max(cells, default=-1) + 1
                rows.append([cells.get(index) for index in range(width)])
            sheets[name] = rows
        return sheets


def padded(row: list[object | None], width: int) -> list[object | None]:
    return row + [None] * max(0, width - len(row))


def text(value: object | None) -> str:
    return "" if value is None else str(value).strip()


def release_id(value: object | None) -> str:
    match = re.match(r"P[0-4]", text(value))
    return match.group(0) if match else ""


def dependencies(value: object | None) -> list[str]:
    return [item.strip() for item in text(value).split(",") if item.strip()]


def body_for(row: list[object | None]) -> str:
    return "\n\n".join([
        f"Logical ID: {text(row[0])}",
        text(row[11]),
        f"Acceptance Criteria\n- {text(row[12])}",
        f"Non-goal\n- {text(row[13])}",
        f"Dependencies\n- {text(row[18]) or 'None'}",
        f"Verification\n- {text(row[22])}",
    ])


def main() -> int:
    errors: list[str] = []
    sheets = read_workbook(WORKBOOK)
    required_sheets = {"Roadmap", "需求总表", "Jira-Standard", "Jira-Advanced", "GitHub", "字段字典"}
    if set(sheets) != required_sheets:
        errors.append(f"sheet set mismatch: {sorted(sheets)}")

    master = sheets.get("需求总表", [])
    if not master:
        errors.append("需求总表 is empty")
        return report(errors)
    header = padded(master[0], len(MASTER_HEADERS))[: len(MASTER_HEADERS)]
    if header != MASTER_HEADERS:
        errors.append("需求总表 headers do not match the 30-column contract")

    records: dict[str, list[object | None]] = {}
    counts = {level: 0 for level in ("Roadmap", "Epic", "Story", "Task")}
    for row_number, raw in enumerate(master[1:], start=2):
        row = padded(raw, len(MASTER_HEADERS))[: len(MASTER_HEADERS)]
        logical_id = text(row[0])
        if not logical_id:
            errors.append(f"需求总表 row {row_number}: missing ID")
            continue
        if logical_id in records:
            errors.append(f"duplicate ID: {logical_id}")
        records[logical_id] = row
        expected_level = next((level for prefix, level in LEVEL_PREFIX.items() if logical_id.startswith(prefix)), None)
        if row[2] != expected_level:
            errors.append(f"{logical_id}: Level={row[2]!r}, expected {expected_level!r}")
        if expected_level:
            counts[expected_level] += 1
        parent = text(row[1])
        if expected_level == "Roadmap" and parent:
            errors.append(f"{logical_id}: Roadmap must not have Parent ID")
        if expected_level != "Roadmap" and not parent:
            errors.append(f"{logical_id}: missing Parent ID")
        if text(row[14]) not in PRIORITIES:
            errors.append(f"{logical_id}: invalid Priority {row[14]!r}")
        if text(row[15]) not in STATUSES:
            errors.append(f"{logical_id}: invalid Status {row[15]!r}")
        if text(row[16]) not in OWNER_ROLES:
            errors.append(f"{logical_id}: invalid Owner Role {row[16]!r}")
        if text(row[19]) not in RISKS:
            errors.append(f"{logical_id}: invalid Risk {row[19]!r}")
        if expected_level == "Story":
            if text(row[16]) not in STORY_OWNER_ROLES:
                errors.append(f"{logical_id}: Story Owner Role is not platform-compatible")
            if not isinstance(row[17], (int, float)) or isinstance(row[17], bool) or row[17] <= 0:
                errors.append(f"{logical_id}: Story Points must be a positive number, got {row[17]!r}")
            if not text(row[22]):
                errors.append(f"{logical_id}: missing Verification")
            elif text(row[3]) not in text(row[22]):
                errors.append(f"{logical_id}: Verification must identify the Story title")
            if not text(row[28]).startswith("ZW-PRD-001 §"):
                errors.append(f"{logical_id}: Source must include a PRD section anchor")
        for column, label in ((20, "Architecture Ref"), (21, "UX Ref")):
            ref = text(row[column])
            if ref and (re.match(r"^[A-Za-z]:[/\\]", ref) or ref.startswith("/")):
                errors.append(f"{logical_id}: {label} must be repository-relative")

    expected_counts = {"Roadmap": 6, "Epic": 18, "Story": 68, "Task": 12}
    if counts != expected_counts:
        errors.append(f"level counts mismatch: {counts}")

    for logical_id, row in records.items():
        parent = text(row[1])
        if parent:
            if parent not in records:
                errors.append(f"{logical_id}: unknown parent {parent}")
            else:
                allowed = {"Epic": "Roadmap", "Story": "Epic", "Task": "Story"}.get(text(row[2]))
                if text(records[parent][2]) != allowed:
                    errors.append(f"{logical_id}: parent {parent} has level {records[parent][2]!r}, expected {allowed!r}")
        for dependency in dependencies(row[18]):
            if dependency not in records:
                errors.append(f"{logical_id}: unknown dependency {dependency}")
                continue
            if text(records[dependency][2]) != "Story":
                errors.append(f"{logical_id}: dependency {dependency} is not a Story")
                continue
            current_release = release_id(row[8])
            dependency_release = release_id(records[dependency][8])
            if current_release in RELEASE_ORDER and dependency_release in RELEASE_ORDER and RELEASE_ORDER[dependency_release] > RELEASE_ORDER[current_release]:
                errors.append(f"{logical_id}: release {current_release} depends on later {dependency} ({dependency_release})")

    story_graph = {
        logical_id: [dependency for dependency in dependencies(row[18]) if dependency in records and text(records[dependency][2]) == "Story"]
        for logical_id, row in records.items() if text(row[2]) == "Story"
    }
    visit_state: dict[str, int] = {}
    visit_stack: list[str] = []

    def visit(story_id: str) -> None:
        state = visit_state.get(story_id, 0)
        if state == 2:
            return
        if state == 1:
            cycle_start = visit_stack.index(story_id)
            errors.append(f"dependency cycle: {' -> '.join(visit_stack[cycle_start:] + [story_id])}")
            return
        visit_state[story_id] = 1
        visit_stack.append(story_id)
        for dependency in story_graph.get(story_id, []):
            visit(dependency)
        visit_stack.pop()
        visit_state[story_id] = 2

    for story_id in story_graph:
        visit(story_id)

    for story_id, required_terms in KPI_ACCEPTANCE.items():
        acceptance = text(records.get(story_id, [None] * len(MASTER_HEADERS))[12])
        for term in required_terms:
            if term not in acceptance:
                errors.append(f"{story_id}: KPI acceptance is missing {term!r}")

    roadmap_story_ids = set(re.findall(r"ZW-ST-\d{4}", ROADMAP.read_text(encoding="utf-8")))
    workbook_story_ids = {logical_id for logical_id, row in records.items() if row[2] == "Story"}
    if roadmap_story_ids != workbook_story_ids:
        errors.append(f"roadmap.yaml Story IDs mismatch: missing={sorted(workbook_story_ids-roadmap_story_ids)}, extra={sorted(roadmap_story_ids-workbook_story_ids)}")

    global_number = {logical_id: index for index, logical_id in enumerate(records, start=1)}
    for sheet_name, expected_header in VIEW_HEADERS.items():
        rows = sheets.get(sheet_name, [])
        if not rows or padded(rows[0], len(expected_header))[: len(expected_header)] != expected_header:
            errors.append(f"{sheet_name}: header mismatch")
            continue
        expected_ids = [logical_id for logical_id, row in records.items() if sheet_name != "Jira-Standard" or row[2] != "Roadmap"]
        id_column = 9 if sheet_name.startswith("Jira") else 4
        actual_ids = [text(padded(row, len(expected_header))[id_column]) for row in rows[1:]]
        if actual_ids != expected_ids:
            errors.append(f"{sheet_name}: Logical ID order/content mismatch")
            continue
        for row_number, raw in enumerate(rows[1:], start=2):
            view = padded(raw, len(expected_header))
            logical_id = text(view[id_column])
            source = records[logical_id]
            if sheet_name == "GitHub":
                expected = [
                    f"[{logical_id}] {text(source[3])}", body_for(source), text(source[26]), text(source[1]), logical_id,
                    text(source[15]), text(source[14]), text(source[8]), text(source[27]), source[17], text(source[18]), text(source[23]),
                ]
                actual = [text(view[index]) if index not in {9} else view[index] for index in range(len(expected))]
                comparable = [text(value) if index not in {9} else value for index, value in enumerate(expected)]
                if actual != comparable:
                    errors.append(f"GitHub row {row_number}: full field mapping mismatch for {logical_id}")
            else:
                expected_parent_number = global_number.get(text(source[1]))
                if sheet_name == "Jira-Standard" and source[2] == "Epic":
                    expected_parent_number = None
                labels = text(source[27])
                if sheet_name == "Jira-Standard":
                    labels = f"{labels},{text(source[4]).lower()}"
                expected = [
                    global_number[logical_id], text(source[24] if sheet_name == "Jira-Standard" else source[25]),
                    text(source[3]), body_for(source), expected_parent_number, text(source[14]), labels, text(source[8]),
                    source[17], logical_id, text(source[1]),
                ]
                if sheet_name == "Jira-Standard":
                    expected.extend([text(source[5]), text(source[15])])
                else:
                    expected.append(text(source[15]))
                actual = [view[index] if index in {0, 4, 8} else text(view[index]) for index in range(len(expected))]
                comparable = [value if index in {0, 4, 8} else text(value) for index, value in enumerate(expected)]
                if actual != comparable:
                    errors.append(f"{sheet_name} row {row_number}: full field mapping mismatch for {logical_id}")

    return report(errors)


def report(errors: list[str]) -> int:
    if errors:
        print("Home Intelligence requirements validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Home Intelligence requirements validation passed: hierarchy, enums, release order, dependency DAG, KPI traceability and all import-view fields are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
