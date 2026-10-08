#!/usr/bin/env python3
"""Validate the English planning index, Markdown metadata and local traceability.

Uses only the standard library. The frontmatter subset is YAML with JSON values,
as defined in the planning templates. This is a documentation gate, not a runtime
or independent implementation acceptance test.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = Path("docs/product/home-intelligence")
FEATURE_STATES = {"planned", "active", "completed", "paused", "cancelled"}
STORY_STATES = {"draft", "ready", "active", "blocked", "done", "cancelled"}
# The REQ-012 delivery contract is fixed. Advancing refinement requires an
# explicit scope/policy change, not just changing a roadmap stage status.
REFINEMENT_BOUNDARY = {
    "id": "REQ-012-R1",
    "active_stage": "R1",
    "permitted_story_stages": ["R1"],
    "expected_feature_count": 20,
    "expected_story_count": 30,
    "feature_counts_by_stage": {"R1": 10, "R2": 10},
    "stage_statuses": {f"R{i}": "active" if i == 1 else "planned" for i in range(1, 13)},
}
FEATURE_SECTIONS = {
    "Outcome",
    "User / System Value",
    "Scope",
    "Non-goals",
    "Architecture Boundaries",
    "Acceptance Criteria",
    "Dependencies",
    "Stories",
    "Demo Scenario",
    "Risks / Open Questions",
}
STORY_SECTIONS = {
    "Context",
    "Outcome",
    "Scope",
    "Non-goals",
    "Acceptance Criteria",
    "Technical Notes",
    "Dependencies",
    "Verification",
    "Definition of Done",
    "Implementation Checklist",
}


def metadata(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    if not source.startswith("---\n") or "\n---\n" not in source[4:]:
        raise ValueError("missing YAML frontmatter")
    block = source[4:].split("\n---\n", 1)[0]
    result = {}
    for line in block.splitlines():
        key, separator, value = line.partition(":")
        if not separator or key in result:
            raise ValueError("invalid or duplicate frontmatter key")
        result[key] = json.loads(value.strip())
    return result


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    product = root / PRODUCT
    planning = product / "requirements"
    try:
        index = json.loads((planning / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"Cannot read planning index: {exc}"]
    if index.get("schema_version") != 1:
        errors.append("Unsupported index schema version")
    if index.get("refinement_boundary") != REFINEMENT_BOUNDARY:
        errors.append("Refinement boundary policy must match the approved REQ-012-R1 contract")
    for plural, count_key in (
        ("features", "expected_feature_count"),
        ("stories", "expected_story_count"),
    ):
        entries = index.get(plural)
        expected = REFINEMENT_BOUNDARY[count_key]
        if not isinstance(entries, list) or len(entries) != expected:
            errors.append(f"Expected exactly {expected} {plural} in the REQ-012 boundary")
    objects: dict[str, dict] = {}
    groups: dict[str, dict[str, dict]] = {}
    for plural, kind, states in (
        ("stages", "stage", FEATURE_STATES),
        ("features", "feature", FEATURE_STATES),
        ("stories", "story", STORY_STATES),
    ):
        entries = index.get(plural)
        if not isinstance(entries, list) or not entries:
            errors.append(f"Missing or empty {plural}")
            groups[plural] = {}
            continue
        group = {}
        pattern = r"R\d+" if kind == "stage" else rf"HI-{'F' if kind == 'feature' else 'S'}\d{{3}}"
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"Invalid {kind} object")
                continue
            ident = entry.get("id")
            if not isinstance(ident, str) or not re.fullmatch(pattern, ident):
                errors.append(f"Invalid {kind} ID: {ident!r}")
                continue
            if ident in objects:
                errors.append(f"Duplicate ID: {ident}")
            if entry.get("status") not in states:
                errors.append(f"Invalid state for {ident}")
            objects[ident] = entry
            group[ident] = entry
        groups[plural] = group
    stages, features, stories = (groups[key] for key in ("stages", "features", "stories"))
    if set(stages) != {f"R{i}" for i in range(1, 13)}:
        errors.append("Roadmap must retain R1 through R12")
    if index.get("active_stage") != REFINEMENT_BOUNDARY["active_stage"]:
        errors.append("REQ-012 permits only R1 as the active refinement stage")
    for ident, expected_status in REFINEMENT_BOUNDARY["stage_statuses"].items():
        if stages.get(ident, {}).get("status") != expected_status:
            errors.append(f"Refinement boundary requires {ident} status {expected_status}")
    feature_counts = {}
    for entry in features.values():
        stage = entry.get("stage")
        feature_counts[stage] = feature_counts.get(stage, 0) + 1
    if feature_counts != REFINEMENT_BOUNDARY["feature_counts_by_stage"]:
        errors.append("Refinement boundary requires exactly ten R1 and ten R2 Features")
    active = index.get("active_stage")
    if [ident for ident, entry in stages.items() if entry.get("status") == "active"] != [active]:
        errors.append("Exactly the declared active stage must be active")
    documentation_req = index.get("documentation_req")
    documentation_paths = [
        root / f"harness/tasks/features/{documentation_req}.md",
        root / f"harness/tasks/archive/done/features/{documentation_req}.md",
    ]
    if not any(path.is_file() for path in documentation_paths):
        errors.append("Missing documentation Harness REQ")
    roadmap = (product / "ROADMAP.md").read_text(encoding="utf-8")
    for ident, entry in stages.items():
        if f"### {ident} — {entry.get('title')}" not in roadmap:
            errors.append(f"Missing roadmap heading: {ident}")
        for key in ("goal", "capabilities", "exit_criteria", "dependencies"):
            if not entry.get(key) or entry[key] not in roadmap:
                errors.append(f"Roadmap/index {key} mismatch: {ident}")
        section = re.split(r"\n### |\n## ", roadmap.split(f"### {ident} —", 1)[-1])[0]
        if f"**Status:** `{entry.get('status')}`" not in section:
            errors.append(f"Roadmap/index status mismatch: {ident}")
    legacy = (product / "roadmap.yaml").read_text(encoding="utf-8")
    legacy_ids = set(re.findall(r"ZW-(?:RM|EP|ST|TK)-\d+", legacy))
    checked_paths: set[Path] = set()
    for plural, kind, required in (
        ("features", "feature", FEATURE_SECTIONS),
        ("stories", "story", STORY_SECTIONS),
    ):
        for ident, entry in groups[plural].items():
            relative = entry.get("path")
            if not isinstance(relative, str):
                errors.append(f"Missing path: {ident}")
                continue
            path = (planning / relative).resolve()
            if not path.is_relative_to(planning.resolve()) or not path.is_file():
                errors.append(f"Invalid or missing path: {ident}")
                continue
            if path in checked_paths:
                errors.append(f"Duplicate object file: {ident}")
            checked_paths.add(path)
            try:
                front = metadata(path)
            except (OSError, ValueError) as exc:
                errors.append(f"Invalid metadata: {ident}: {exc}")
                continue
            for key in (
                "id",
                "title",
                "stage",
                "status",
                "depends_on",
                "source_ref",
                "legacy_refs",
            ):
                if front.get(key) != entry.get(key):
                    errors.append(f"Index/frontmatter {key} mismatch: {ident}")
            if front.get("type") != kind or front.get("priority") not in {"P0", "P1", "P2", "P3"}:
                errors.append(f"Invalid type or priority: {ident}")
            if entry.get("stage") not in stages:
                errors.append(f"Unknown stage: {ident}")
            if kind == "feature":
                if not isinstance(front.get("owners"), list) or not front["owners"]:
                    errors.append(f"Missing Feature owners: {ident}")
                children = entry.get("stories", [])
                if not isinstance(children, list) or len(children) != len(set(children)):
                    errors.append(f"Invalid Feature child list: {ident}")
                else:
                    expected = {
                        sid for sid, story in stories.items() if story.get("parent") == ident
                    }
                    if set(children) != expected:
                        errors.append(f"Feature child list mismatch: {ident}")
            else:
                parent = entry.get("parent")
                if parent not in features or features[parent].get("stage") != entry.get("stage"):
                    errors.append(f"Invalid Story parent/stage: {ident}")
                for key in ("parent", "harness_ref"):
                    if key not in front or front[key] != entry.get(key):
                        errors.append(f"Index/frontmatter {key} mismatch: {ident}")
                if entry.get("stage") not in REFINEMENT_BOUNDARY["permitted_story_stages"]:
                    errors.append(f"Future-stage Story is outside refinement boundary: {ident}")
                harness = entry.get("harness_ref")
                if harness is not None:
                    candidates = [
                        root / f"harness/tasks/features/{harness}.md",
                        root / f"harness/tasks/archive/done/features/{harness}.md",
                    ]
                    if not any(candidate.is_file() for candidate in candidates):
                        errors.append(f"Missing linked Harness REQ: {ident}")
                elif entry.get("status") in {"active", "done"}:
                    errors.append(f"Engineering state without Harness admission: {ident}")
            refs = entry.get("legacy_refs")
            if not isinstance(refs, list) or any(ref not in legacy_ids for ref in refs):
                errors.append(f"Unknown legacy reference: {ident}")
            source = path.read_text(encoding="utf-8")
            headings = set(re.findall(r"^## (.+)$", source, re.M))
            if not required <= headings:
                errors.append(f"Missing sections: {ident}: {sorted(required - headings)}")
            if "- [ ] " not in source:
                errors.append(f"Missing checkable acceptance criteria: {ident}")
    actual = {
        path.resolve()
        for folder in ("features", "stories")
        for path in (planning / folder).glob("*.md")
    }
    if actual != checked_paths:
        errors.append("Orphan or unindexed Feature/Story file")
    for plural in ("stages", "features", "stories"):
        group = groups[plural]
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(ident: str) -> None:
            if ident in visiting:
                errors.append(f"Dependency cycle at {ident}")
                return
            if ident in visited:
                return
            visiting.add(ident)
            deps = group[ident].get("depends_on")
            if not isinstance(deps, list) or len(deps) != len(set(deps)):
                errors.append(f"Invalid dependency list: {ident}")
                deps = []
            for dep in deps:
                if dep not in group:
                    errors.append(f"Missing {plural} dependency: {ident} -> {dep}")
                else:
                    visit(dep)
            visiting.remove(ident)
            visited.add(ident)

        for ident in group:
            visit(ident)
    if (planning / "tasks").exists():
        errors.append("Persistent planning Tasks are outside the hierarchy")
    # Check only this English planning delivery, not unrelated historical documents.
    docs = list(checked_paths) + list(planning.glob("*.md"))
    docs += [
        product / name
        for name in (
            "README.md",
            "VISION.md",
            "ROADMAP.md",
            "CURRENT_STATE.md",
            "CROSSWALK.md",
            "ARCHITECTURE_ALIGNMENT.md",
            "NFR.md",
            "DEFINITION_OF_DONE.md",
        )
    ]
    for path in docs:
        if not path.is_file():
            errors.append(f"Missing planning document: {path.name}")
            continue
        for target in re.findall(r"\[[^\]\n]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            destination = (path.parent / unquote(target.split("#", 1)[0])).resolve()
            if not destination.is_relative_to(root.resolve()) or not destination.exists():
                errors.append(f"Broken or outside-repo link: {path.relative_to(root)} -> {target}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Home Intelligence planning validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Home Intelligence planning validation passed: metadata, parents, stages, "
        "dependencies, refinement boundary, legacy references and local links."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
