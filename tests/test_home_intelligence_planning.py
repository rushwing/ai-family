"""Regression checks for malformed requirements, isolated from the real backlog."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.check_home_intelligence_planning import PRODUCT, ROOT, validate


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
