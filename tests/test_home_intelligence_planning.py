"""Regression checks for malformed requirements, isolated from the real backlog."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.check_home_intelligence_planning import PRODUCT, REFINEMENT_BOUNDARY, ROOT, validate


class PlanningIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hi-planning-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / PRODUCT, self.root / PRODUCT)
        shutil.copytree(ROOT / "docs/adr", self.root / "docs/adr")
        for rel in ("harness/tasks/features/REQ-012.md", "harness/tasks/features/REQ-011.md"):
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dest)
        self.index = self.root / PRODUCT / "requirements/index.json"
        self.baseline = json.loads(self.index.read_text(encoding="utf-8"))

    def test_published_planning_is_valid(self):
        self.assertEqual(validate(self.root), [])

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
