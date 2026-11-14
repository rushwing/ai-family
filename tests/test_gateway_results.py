"""Required PG evidence cannot pass by skipping or omitting an entire suite."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "gateway_result_gate", _ROOT / "tools/check_gateway_results.py"
)
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)


class GatewayResultGateTests(unittest.TestCase):
    def check(self, xml):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "junit.xml"
            path.write_text(xml)
            return _gate.main(str(path))

    def test_both_executed_suites_required(self):
        self.assertEqual(
            self.check(
                '<testsuite><testcase classname="test_confirmation_pg"/>'
                '<testcase classname="test_registered_home"/></testsuite>'
            ),
            0,
        )
        self.assertEqual(self.check("<testsuite/>"), 1)
        self.assertEqual(
            self.check('<testsuite><testcase classname="test_confirmation_pg"/></testsuite>'), 1
        )

    def test_each_nonpassing_outcome_rejected(self):
        for outcome in ("skipped", "failure", "error"):
            with self.subTest(outcome=outcome):
                self.assertEqual(
                    self.check(
                        '<testsuite><testcase classname="test_confirmation_pg">'
                        f'<{outcome}/></testcase><testcase classname="test_registered_home"/>'
                        "</testsuite>"
                    ),
                    1,
                )


if __name__ == "__main__":
    unittest.main()
