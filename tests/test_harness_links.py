"""Regressions for missing delivery artifacts masked by local files."""
import tempfile
import unittest
from pathlib import Path

from tools.check_harness_links import broken_links


class HarnessLinkTests(unittest.TestCase):
    def test_missing_untracked_and_tracked_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "REQ.md"
            artifact = root / "evidence.json"
            source.write_text("[evidence](evidence.json) [web](https://example.com) [anchor](#ac)")
            self.assertEqual(len(broken_links(root, source, {source})), 1)
            artifact.write_text("{}")
            self.assertEqual(len(broken_links(root, source, {source})), 1)
            self.assertEqual(broken_links(root, source, {source, artifact}), [])

    def test_outside_repo_and_encoded_fragment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "REQ.md"
            artifact = root / "review evidence.md"
            artifact.write_text("# Review")
            source.write_text("[ok](review%20evidence.md#review) [bad](../outside.md)")
            errors = broken_links(root, source, {source, artifact})
            self.assertEqual(errors, ["REQ.md -> ../outside.md"])
