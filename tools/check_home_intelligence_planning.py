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


def harness_paths(root: Path, req_id: str) -> list[Path]:
    if not isinstance(req_id, str) or not re.fullmatch(r"REQ-\d{3}", req_id):
        return []
    return [
        path
        for path in (
            root / f"harness/tasks/features/{req_id}.md",
            root / f"harness/tasks/archive/done/features/{req_id}.md",
        )
        if path.is_file()
    ]


def engineering_state(root: Path, story: dict) -> dict:
    """Read admitted engineering metadata; never persist a second lifecycle."""
    paths = harness_paths(root, story.get("harness_ref"))
    if len(paths) != 1:
        raise ValueError("Expected exactly one linked Harness REQ")
    req = metadata(paths[0])
    return {key: req[key] for key in ("req_id", "status", "owner", "priority", "depends_on")}


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
            admitted = kind == "story" and entry.get("harness_ref") is not None
            if not admitted and entry.get("status") not in states:
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
    admitted_dependencies: dict[str, list[str]] = {}
    claimed_reqs: dict[str, str] = {}
    story_claims: dict[str, list[Path]] = {}
    req_folders = (
        root / "harness/tasks/features",
        root / "harness/tasks/archive/done/features",
    )
    for folder in req_folders:
        for req_path in folder.glob("REQ-*.md"):
            text = req_path.read_text(encoding="utf-8")
            frontmatter = text.split("---", 2)[1] if text.startswith("---") else ""
            claim = re.search(r'^story_ref: *["\']?(HI-S\d{3})["\']? *$', frontmatter, re.M)
            if claim:
                story_claims.setdefault(claim.group(1), []).append(req_path)
    req_to_story = {
        entry.get("harness_ref"): ident
        for ident, entry in stories.items()
        if isinstance(entry.get("harness_ref"), str)
    }
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
            admitted = kind == "story" and entry.get("harness_ref") is not None
            shared_keys = ["id", "title", "stage", "source_ref", "legacy_refs"]
            if not admitted:
                shared_keys += ["status", "depends_on"]
            for key in shared_keys:
                if front.get(key) != entry.get(key):
                    errors.append(f"Index/frontmatter {key} mismatch: {ident}")
            if front.get("type") != kind or (
                not admitted and front.get("priority") not in {"P0", "P1", "P2", "P3"}
            ):
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
                    candidates = harness_paths(root, harness)
                    if len(story_claims.get(ident, [])) > 1:
                        errors.append(f"Multiple Harness specifications claim Story: {ident}")
                    if not candidates:
                        errors.append(f"Missing linked Harness REQ: {ident}")
                    elif len(candidates) != 1:
                        errors.append(f"Duplicate active/archived Harness REQ: {ident}")
                    else:
                        try:
                            req = metadata(candidates[0])
                        except (OSError, ValueError) as exc:
                            errors.append(f"Invalid linked Harness metadata: {ident}: {exc}")
                            req = {}
                        if req.get("req_id") != harness or req.get("story_ref") != ident:
                            errors.append(f"Harness/Story reciprocal identity mismatch: {ident}")
                        if harness in claimed_reqs:
                            errors.append(f"Harness REQ shared by multiple Stories: {ident}")
                        claimed_reqs[harness] = ident
                        req_states = {
                            "draft",
                            "req_review",
                            "tc_design",
                            "tc_review",
                            "tc_impl",
                            "tc_impl_review",
                            "req_impl",
                            "req_impl_review",
                            "pr_draft",
                            "blocked",
                            "done",
                        }
                        registry = (root / "harness/agent-registry.yml").read_text(encoding="utf-8")
                        owners = set(re.findall(r"uid: ([a-z]+-\d{3})", registry))
                        owners.add("unassigned")
                        if req.get("status") not in req_states or req.get("owner") not in owners:
                            errors.append(f"Invalid Harness lifecycle/owner: {ident}")
                        if req.get("priority") not in {"P0", "P1", "P2", "P3"}:
                            errors.append(f"Invalid Harness priority: {ident}")
                        deps = req.get("depends_on")
                        if (
                            not isinstance(deps, list)
                            or any(not isinstance(dep, str) for dep in deps)
                            or len(deps) != len(set(deps))
                        ):
                            errors.append(f"Invalid Harness dependencies: {ident}")
                            deps = []
                        for dep in deps:
                            if len(harness_paths(root, dep)) != 1:
                                errors.append(
                                    f"Missing or duplicate Harness dependency: {ident} -> {dep}"
                                )
                        admitted_dependencies[ident] = [
                            req_to_story[dep] for dep in deps if dep in req_to_story
                        ]
                        req_text = candidates[0].read_text(encoding="utf-8")
                        if not req.get("acceptance") or not re.search(r"- \[[ x]\] ", req_text):
                            errors.append(f"Missing Harness acceptance criteria: {ident}")
                        story_links = re.findall(
                            r"\[[^\]\n]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")
                        )
                        if not any(
                            (path.parent / target.split("#", 1)[0]).resolve()
                            == candidates[0].resolve()
                            for target in story_links
                        ):
                            errors.append(f"Missing canonical Harness link: {ident}")
                    forbidden = {
                        "status",
                        "owner",
                        "priority",
                        "depends_on",
                        "test_case_ref",
                        "acceptance",
                        "review_round",
                        "pending_bugs",
                        "pr_number",
                    }
                    if forbidden.intersection(front) or forbidden.intersection(entry):
                        errors.append(f"Duplicated engineering metadata in admitted Story: {ident}")
                elif entry.get("status") in {"active", "done"}:
                    errors.append(f"Engineering state without Harness admission: {ident}")
            refs = entry.get("legacy_refs")
            if not isinstance(refs, list) or any(ref not in legacy_ids for ref in refs):
                errors.append(f"Unknown legacy reference: {ident}")
            source = path.read_text(encoding="utf-8")
            headings = set(re.findall(r"^## (.+)$", source, re.M))
            if admitted:
                navigation_sections = {"Context", "Outcome", "Engineering Requirement"}
                if not navigation_sections <= headings:
                    errors.append(f"Missing admitted Story navigation sections: {ident}")
                engineering_sections = STORY_SECTIONS - {"Context", "Outcome"}
                if engineering_sections.intersection(headings) or re.search(r"- \[[ x]\] ", source):
                    errors.append(
                        f"Duplicated engineering specification in admitted Story: {ident}"
                    )
            else:
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
            deps = (
                admitted_dependencies.get(ident, [])
                if plural == "stories" and group[ident].get("harness_ref") is not None
                else group[ident].get("depends_on")
            )
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
    index = json.loads((ROOT / PRODUCT / "requirements/index.json").read_text(encoding="utf-8"))
    for story in index["stories"]:
        if story.get("harness_ref") is not None:
            state = engineering_state(ROOT, story)
            print(f"{story['id']} -> {state['req_id']}: {state['status']} / {state['owner']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
