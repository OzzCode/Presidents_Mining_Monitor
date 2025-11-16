"""Deprecated helper script.

This script has been superseded by the dashboard and API endpoints.
If you need similar functionality, prefer:
  - GET /api/miners/current
  - GET /api/metrics?ip=...

Keeping this file as a stub to avoid breaking external references.
"""

import sys


def main() -> int:
    print(
        "helpers/check_miners.py is deprecated. Use the dashboard or /api endpoints instead.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
