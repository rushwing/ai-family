"""Evidence gate rejects partial, duplicated, renamed or nonpassing reports."""

import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "gateway_result_gate", _ROOT / "tools/check_gateway_results.py"
)
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)


def report():
    root = ET.Element("testsuite")
    for module, names in _gate.REQUIRED.items():
        for name in names:
            ET.SubElement(
                root, "testcase", classname="toolsets.mcp.gateway.tests." + module, name=name
            )
    return root


class GatewayResultGateTests(unittest.TestCase):
    def check(self, root):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "junit.xml"
            path.write_text(ET.tostring(root, encoding="unicode"))
            return _gate.main(str(path))

    def test_complete_report_passes(self):
        self.assertEqual(self.check(report()), 0)

    def test_manifest_retains_all_original_51_cases(self):
        evidence = json.loads(
            (_ROOT / "harness/tasks/evidence/REQ-003-004-prerequisite-provenance.json").read_text()
        )
        self.assertEqual(len(evidence["required_cases"]), 51)
        for case in evidence["required_cases"]:
            self.assertIn(case["name"], _gate.REQUIRED[case["module"]])
        for names in _gate.REQUIRED.values():
            self.assertEqual(len(names), len(set(names)))

    def test_each_partial_omission_rejected(self):
        # Remove every required parameterized identity in turn, not just a suite.
        for index in range(len(report())):
            root = report()
            with self.subTest(missing=root[index].get("name")):
                root.remove(root[index])
                self.assertEqual(self.check(root), 1)

    def test_original_two_case_probe_rejected(self):
        root = ET.Element("testsuite")
        for module in _gate.REQUIRED:
            ET.SubElement(root, "testcase", classname=module, name="passing_probe")
        self.assertEqual(self.check(root), 1)
        self.assertEqual(self.check(ET.Element("testsuite")), 1)

    def test_duplicate_or_renamed_case_cannot_fill_omission(self):
        for kind in ("duplicate", "rename", "spoof_module"):
            root = report()
            with self.subTest(kind=kind):
                if kind == "duplicate":
                    root[-1].set("name", root[-2].get("name"))
                elif kind == "rename":
                    root[-1].set("name", "replacement_test")
                else:
                    root[-1].set("classname", "spoof_" + root[-1].get("classname").split(".")[-1])
                self.assertEqual(self.check(root), 1)

    def test_each_nonpassing_outcome_rejected(self):
        for outcome in ("skipped", "failure", "error"):
            for index in (0, len(report()) - 1):
                with self.subTest(outcome=outcome, index=index):
                    root = report()
                    ET.SubElement(root[index], outcome)
                    self.assertEqual(self.check(root), 1)

    def test_unpinned_suite_failure_also_rejected(self):
        root = report()
        case = ET.SubElement(
            root, "testcase", classname="test_registered_home", name="new_regression"
        )
        ET.SubElement(case, "failure")
        self.assertEqual(self.check(root), 1)

    def test_missing_or_malformed_report_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "junit.xml"
            self.assertEqual(_gate.main(str(path)), 1)
            path.write_text("<broken")
            self.assertEqual(_gate.main(str(path)), 1)


if __name__ == "__main__":
    unittest.main()
