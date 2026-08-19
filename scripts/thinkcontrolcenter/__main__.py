"""Allow running the package with ``python3 -m thinkcontrolcenter``."""

import sys

from thinkcontrolcenter.app import main

if __name__ == "__main__":
    sys.exit(main())
