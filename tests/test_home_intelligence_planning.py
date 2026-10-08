"""Regression checks for malformed requirements, isolated from the real backlog."""

from __future__ import annotations

import copy
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.check_home_intelligence_planning import (
    PRODUCT,
    REFINEMENT_BOUNDARY,
    ROOT,
    engineering_state,
    validate,
)


class PlanningIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hi-planning-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / PRODUCT, self.root / PRODUCT)
        shutil.copytree(ROOT / "docs/adr", self.root / "docs/adr")
        for rel in (
            "harness/tasks/archive/done/features/REQ-012.md",
            "harness/tasks/archive/done/features/REQ-011.md",
            "harness/tasks/features/REQ-013.md",
            "harness/agent-registry.yml",
        ):
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            source = ROOT / rel
            if rel == 'harness/tasks/features/REQ-013.md' and not source.exists():
                source = ROOT / 'harness/tasks/archive/done/features/REQ-013.md'
            shutil.copy2(source, dest)
        # Keep lifecycle mutation fixtures active even after the live REQ is archived.
        for path in (self.root / PRODUCT).rglob('*.md'):
            text = path.read_text()
            path.write_text(text.replace('tasks/archive/done/features/REQ-013.md',
                                         'tasks/features/REQ-013.md'))
        self.index = self.root / PRODUCT / "requirements/index.json"
        self.baseline = json.loads(self.index.read_text(encoding="utf-8"))

    def test_published_planning_is_valid(self):
        self.assertEqual(validate(self.root), [])

    def test_admitted_story_reads_engineering_state_from_harness(self):
        story = next(s for s in self.baseline["stories"] if s["id"] == "HI-S008")
        self.assertNotIn("status", story)
        self.assertNotIn("depends_on", story)
        req = self.root / "harness/tasks/features/REQ-013.md"
        # Control this fixture's lifecycle independently of the live backlog.
        text = re.sub(r'^status: .*$', 'status: "req_review"', req.read_text(), count=1, flags=re.M)
        text = re.sub(r'^owner: .*$', 'owner: "evaluator-001"', text, count=1, flags=re.M)
        req.write_text(text)
        self.assertEqual(engineering_state(self.root, story)["status"], "req_review")
        req.write_text(req.read_text().replace('status: "req_review"', 'status: "tc_design"'))
        self.assertEqual(engineering_state(self.root, story)["status"], "tc_design")
        self.assertEqual(validate(self.root), [])

    def test_admitted_story_rejects_copied_engineering_metadata(self):
        story = next(s for s in self.baseline["stories"] if s["id"] == "HI-S008")
        story["status"] = "done"
        self.index.write_text(json.dumps(self.baseline), encoding="utf-8")
        self.assertIn(
            "Duplicated engineering metadata in admitted Story: HI-S008", validate(self.root)
        )

    def test_admitted_story_rejects_copied_acceptance(self):
        story = self.root / PRODUCT / "requirements/stories/HI-S008.md"
        story.write_text(story.read_text() + "\n## Acceptance Criteria\n\n- [ ] Copied criterion\n")
        self.assertIn(
            "Duplicated engineering specification in admitted Story: HI-S008", validate(self.root)
        )

    def test_admitted_story_requires_reciprocal_req_identity(self):
        req = self.root / "harness/tasks/features/REQ-013.md"
        req.write_text(req.read_text().replace('story_ref: "HI-S008"', 'story_ref: "HI-S009"'))
        self.assertIn("Harness/Story reciprocal identity mismatch: HI-S008", validate(self.root))

    def test_admitted_story_rejects_a_second_authoritative_req(self):
        req = self.root / "harness/tasks/features/REQ-013.md"
        duplicate = self.root / "harness/tasks/features/REQ-014.md"
        duplicate.write_text(req.read_text().replace("REQ-013", "REQ-014"))
        self.assertIn("Multiple Harness specifications claim Story: HI-S008", validate(self.root))

    def test_admitted_story_requires_existing_req(self):
        (self.root / "harness/tasks/features/REQ-013.md").unlink()
        self.assertIn("Missing linked Harness REQ: HI-S008", validate(self.root))

    def test_admitted_story_supports_archive_and_rejects_duplicate_records(self):
        active = self.root / "harness/tasks/features/REQ-013.md"
        archived = self.root / "harness/tasks/archive/done/features/REQ-013.md"
        shutil.copy2(active, archived)
        self.assertIn("Duplicate active/archived Harness REQ: HI-S008", validate(self.root))
        active.unlink()
        for doc in (self.root / PRODUCT).rglob("*.md"):
            doc.write_text(
                doc.read_text().replace(
                    "tasks/features/REQ-013.md", "tasks/archive/done/features/REQ-013.md"
                )
            )
        archived.write_text(
            re.sub(r'^status: .*$', 'status: "done"', archived.read_text(), count=1, flags=re.M)
        )
        self.assertEqual(validate(self.root), [])
        story = next(s for s in self.baseline["stories"] if s["id"] == "HI-S008")
        self.assertEqual(engineering_state(self.root, story)["status"], "done")

    def test_apartment_specification_fixture_has_consistent_targets(self):
        fixture = self.root / PRODUCT / "examples/three-bedroom-apartment.example.json"
        data = json.loads(fixture.read_text())
        home_id = data["home"]["id"]
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["home"]["residence_type"], "apartment")
        objects = [data["home"]] + [
            item
            for key in ("floors", "areas", "devices", "labels", "area_groups")
            for item in data[key]
        ]
        ids = [item["id"] for item in objects]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(data["floors"][0]["level"], 0)
        floors = {f["id"] for f in data["floors"]}
        labels = {label["id"] for label in data["labels"]}
        areas = {area["id"]: area for area in data["areas"]}
        for item in data["floors"] + data["areas"] + data["devices"]:
            self.assertEqual(item["home_id"], home_id)
        for area in areas.values():
            self.assertIn(area["floor_id"], floors)
            self.assertLessEqual(set(area["labels"]), labels)
        for device in data["devices"]:
            self.assertIn(device["area_id"], areas)
            self.assertNotIn("entity_id", device)
        bedrooms = [a for a in areas.values() if a["area_type"] == "bedroom"]
        self.assertEqual(
            {a["name"] for a in bedrooms}, {"Master Bedroom", "Daughter's Room", "Elderly Bedroom"}
        )
        self.assertEqual(
            [a["id"] for a in bedrooms if "children" in a["labels"]], ["area-bedroom-02"]
        )
        self.assertNotIn("childen", labels)
        groups = {group["id"]: group["area_types"] for group in data["area_groups"]}
        self.assertEqual(
            set(groups),
            {
                "daily_life",
                "resting",
                "kitchen_bath",
                "studio",
                "traffic",
                "storage_utility",
                "outdoor_spaces",
            },
        )
        self.assertEqual(groups["resting"], ["bedroom"])
        for group in ("studio", "storage_utility"):
            self.assertFalse(any(a["area_type"] in groups[group] for a in areas.values()))

    def test_active_documentation_req_is_valid(self):
        archived = self.root / "harness/tasks/archive/done/features/REQ-012.md"
        active = self.root / "harness/tasks/features/REQ-012.md"
        active.parent.mkdir(parents=True, exist_ok=True)
        archived.rename(active)
        readme = self.root / PRODUCT / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace(
                "tasks/archive/done/features/REQ-012.md", "tasks/features/REQ-012.md"
            ),
            encoding="utf-8",
        )
        self.assertEqual(validate(self.root), [])

    def test_missing_documentation_req_is_rejected(self):
        (self.root / "harness/tasks/archive/done/features/REQ-012.md").unlink()
        self.assertIn("Missing documentation Harness REQ", validate(self.root))

    def add_valid_story(self, stage="R1", parent="HI-F001"):
        """Add a complete indexed Story, with matching frontmatter and parent list."""
        data = copy.deepcopy(self.baseline)
        story = copy.deepcopy(data["stories"][0])
        story.update(
            id="HI-S031", path="stories/HI-S031.md", source_ref="S031", stage=stage, parent=parent
        )
        data["stories"].append(story)
        feature = next(entry for entry in data["features"] if entry["id"] == parent)
        feature["stories"].append(story["id"])
        planning = self.root / PRODUCT / "requirements"
        text = (planning / self.baseline["stories"][0]["path"]).read_text(encoding="utf-8")
        text = text.replace("HI-S001", "HI-S031").replace(
            'source_ref: "S001"', 'source_ref: "S031"'
        )
        text = text.replace('stage: "R1"', f'stage: "{stage}"')
        text = text.replace("HI-F001", parent)
        (planning / story["path"]).write_text(text, encoding="utf-8")
        feature_path = planning / feature["path"]
        text = feature_path.read_text(encoding="utf-8")
        head, rest = text.split("## Stories\n\n", 1)
        _, tail = rest.split("\n\n## Demo Scenario", 1)
        links = "\n".join(f"- [{sid}](../stories/{sid}.md)" for sid in feature["stories"])
        feature_path.write_text(
            head + "## Stories\n\n" + links + "\n\n## Demo Scenario" + tail, encoding="utf-8"
        )
        return data

    def complete_r2(self, data):
        """Match both roadmap and index so only the scope policy rejects this."""
        next(stage for stage in data["stages"] if stage["id"] == "R2")["status"] = "completed"
        roadmap = self.root / PRODUCT / "ROADMAP.md"
        text = roadmap.read_text(encoding="utf-8")
        head, tail = text.split("### R2 —", 1)
        roadmap.write_text(
            head + "### R2 —" + tail.replace("**Status:** `planned`", "**Status:** `completed`", 1),
            encoding="utf-8",
        )

    def test_additional_valid_r1_story_exceeds_fixed_boundary(self):
        data = self.add_valid_story()
        self.index.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(
            validate(self.root), ["Expected exactly 30 stories in the REQ-012 boundary"]
        )

    def test_valid_r2_story_is_rejected_even_after_stage_completion(self):
        data = self.add_valid_story(stage="R2", parent="HI-F101")
        self.complete_r2(data)
        self.index.write_text(json.dumps(data), encoding="utf-8")
        self.assertCountEqual(
            validate(self.root),
            [
                "Expected exactly 30 stories in the REQ-012 boundary",
                "Refinement boundary requires R2 status planned",
                "Future-stage Story is outside refinement boundary: HI-S031",
            ],
        )

    def test_r2_story_is_rejected_with_count_unchanged(self):
        data = self.add_valid_story(stage="R2", parent="HI-F101")
        self.complete_r2(data)
        data["stories"] = [story for story in data["stories"] if story["id"] != "HI-S030"]
        feature = next(entry for entry in data["features"] if entry["id"] == "HI-F010")
        feature["stories"].remove("HI-S030")
        planning = self.root / PRODUCT / "requirements"
        (planning / "stories/HI-S030.md").unlink()
        feature_path = planning / feature["path"]
        feature_path.write_text(
            feature_path.read_text(encoding="utf-8").replace(
                "- [HI-S030](../stories/HI-S030.md)\n", ""
            ),
            encoding="utf-8",
        )
        crosswalk = self.root / PRODUCT / "CROSSWALK.md"
        crosswalk.write_text(
            "\n".join(
                line
                for line in crosswalk.read_text(encoding="utf-8").splitlines()
                if "[HI-S030]" not in line
            )
            + "\n",
            encoding="utf-8",
        )
        self.index.write_text(json.dumps(data), encoding="utf-8")
        self.assertCountEqual(
            validate(self.root),
            [
                "Refinement boundary requires R2 status planned",
                "Future-stage Story is outside refinement boundary: HI-S031",
            ],
        )

    def test_additional_valid_feature_exceeds_fixed_boundary(self):
        data = copy.deepcopy(self.baseline)
        feature = copy.deepcopy(next(f for f in data["features"] if f["id"] == "HI-F101"))
        feature.update(id="HI-F111", path="features/HI-F111.md", source_ref="F111")
        data["features"].append(feature)
        planning = self.root / PRODUCT / "requirements"
        text = (planning / "features/HI-F101.md").read_text(encoding="utf-8")
        text = text.replace("HI-F101", "HI-F111").replace(
            'source_ref: "F101"', 'source_ref: "F111"'
        )
        (planning / feature["path"]).write_text(text, encoding="utf-8")
        self.index.write_text(json.dumps(data), encoding="utf-8")
        self.assertCountEqual(
            validate(self.root),
            [
                "Expected exactly 20 features in the REQ-012 boundary",
                "Refinement boundary requires exactly ten R1 and ten R2 Features",
            ],
        )

    def test_policy_cannot_be_silently_relaxed(self):
        data = copy.deepcopy(self.baseline)
        data["refinement_boundary"]["expected_story_count"] = 31
        data["refinement_boundary"]["permitted_story_stages"].append("R2")
        self.index.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(
            validate(self.root),
            ["Refinement boundary policy must match the approved REQ-012-R1 contract"],
        )

    def test_missing_policy_is_rejected(self):
        data = copy.deepcopy(self.baseline)
        del data["refinement_boundary"]
        self.index.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(
            validate(self.root),
            ["Refinement boundary policy must match the approved REQ-012-R1 contract"],
        )

    def test_published_counts_and_story_stage_match_approved_contract(self):
        self.assertEqual(self.baseline["refinement_boundary"], REFINEMENT_BOUNDARY)
        self.assertEqual(len(self.baseline["features"]), 20)
        self.assertEqual(len(self.baseline["stories"]), 30)
        self.assertEqual({story["stage"] for story in self.baseline["stories"]}, {"R1"})

    def test_invalid_relationships_and_metadata_are_rejected(self):
        cases = (
            (
                "duplicate",
                lambda d: d["stories"].append(copy.deepcopy(d["stories"][0])),
                "Duplicate ID",
            ),
            ("parent", lambda d: d["stories"][0].update(parent="HI-F999"), "Invalid Story parent"),
            ("future", lambda d: d["stories"][0].update(stage="R2"), "Future-stage Story"),
            ("cycle", lambda d: d["stories"][0].update(depends_on=["HI-S002"]), "Dependency cycle"),
            (
                "dependency",
                lambda d: d["stories"][0].update(depends_on=["HI-S999"]),
                "Missing stories dependency",
            ),
            (
                "metadata",
                lambda d: d["stories"][0].update(title="drift"),
                "Index/frontmatter title mismatch",
            ),
            (
                "legacy",
                lambda d: d["stories"][0].update(legacy_refs=["ZW-ST-9999"]),
                "Unknown legacy reference",
            ),
            ("stage", lambda d: d["features"][0].update(stage="R99"), "Unknown stage"),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label):
                data = copy.deepcopy(self.baseline)
                mutate(data)
                self.index.write_text(json.dumps(data), encoding="utf-8")
                self.assertTrue(any(expected in error for error in validate(self.root)))

    def test_unindexed_requirement_is_rejected(self):
        orphan = self.root / PRODUCT / "requirements/stories/HI-S999.md"
        orphan.write_text("orphan", encoding="utf-8")
        self.assertIn("Orphan or unindexed Feature/Story file", validate(self.root))

    def test_broken_document_link_is_rejected(self):
        document = self.root / PRODUCT / "VISION.md"
        document.write_text(
            document.read_text(encoding="utf-8") + "\n[bad](missing.md)\n", encoding="utf-8"
        )
        self.assertTrue(
            any("Broken or outside-repo link" in error for error in validate(self.root))
        )


if __name__ == "__main__":
    unittest.main()
