"""Guard the literal fabric acceptance command; changes require mutation tests."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = frozenset((
    "--require-provider-runtime", "--require-demo-runtime", "--require-conformance-runtime",
    "--require-ha-configuration-runtime", "--require-ha-rest-runtime",
    "--require-ha-websocket-runtime", "--require-ha-health-runtime",
    "--require-ha-subscription-runtime", "--require-ha-normalization-runtime",
    "--require-state-store-runtime",
))


def validate(text: str) -> list[str]:
    # Deliberately recognize the checked-in folded run block, not arbitrary YAML
    # or shell programs that could merely echo a flag without executing pytest.
    job = re.search(r"^  home-device-fabric-tc:\n(.*?)(?=^  [\w-]+:|\Z)",
                    text, re.MULTILINE | re.DOTALL)
    if job is None:
        return ["missing fabric acceptance job"]
    step = re.search(
        r"^      - name: Run provider TCs without skips\n"
        r"        run: >-\n((?: {10}[^\n]*\n)+)", job[1], re.MULTILINE,
    )
    if step is None:
        return ["missing literal fabric pytest acceptance command"]
    command = shlex.split(step[1])
    if (command[:3] != ["python", "-m", "pytest"]
            or "toolsets/iot/home-device-fabric/tests" not in command):
        return ["fabric acceptance must execute the complete pytest suite"]
    missing = sorted(REQUIRED.difference(command))
    return ["missing fabric acceptance flag: " + flag for flag in missing]


def main() -> int:
    errors = validate((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    for error in errors:
        print(error)
    if not errors:
        print("Fabric CI wiring passed: complete suite and all ten required-runtime flags.")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
