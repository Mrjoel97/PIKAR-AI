"""Fail when workflow defect register contains open P0/P1 defects."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFECT_REGISTER = ROOT / "plans/workflow_defect_register.md"
SEVERITIES = {"P0", "P1"}
CLOSED_STATES = {"closed", "resolved", "done"}


def main() -> int:
    if not DEFECT_REGISTER.exists():
        print(f"[FAIL] Missing defect register: {DEFECT_REGISTER}")
        return 1

    lines = DEFECT_REGISTER.read_text(encoding="utf-8").splitlines()
    blocking: list[str] = []

    # Expect table rows like: | ID | Severity | Status | ...
    row_pattern = re.compile(r"^\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|")
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        if "---" in line:
            continue
        if "Severity" in line and "Status" in line:
            continue

        match = row_pattern.match(line)
        if not match:
            continue
        defect_id = match.group(1).strip()
        severity = match.group(2).strip().upper()
        status = match.group(3).strip().lower()

        if severity in SEVERITIES and status not in CLOSED_STATES:
            blocking.append(f"{defect_id} ({severity}, {status})")

    if blocking:
        print("[FAIL] Open blocking defects detected:")
        for item in blocking:
            print(f"  - {item}")
        return 1

    print("[PASS] No open P0/P1 workflow defects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
