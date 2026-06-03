"""Frozen-app entry point. PyInstaller bundles this; it starts the GUI.

`--selftest` imports the heavy dependencies and core modules, then exits — a
headless way to confirm the bundle is complete (no GUI window needed).
"""

import sys


def _selftest() -> int:
    import openpyxl
    import pydicom

    from mia.core import common, deliver, dicomdir, inventory, ripper  # noqa: F401
    from mia.gui import app  # noqa: F401

    print(f"selftest OK: pydicom {pydicom.__version__}, "
          f"openpyxl {openpyxl.__version__}")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    from mia.gui.app import main as gui_main
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
