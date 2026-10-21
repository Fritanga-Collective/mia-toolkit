"""Frozen-app entry point. PyInstaller bundles this; it starts the GUI.

Headless flags (no GUI window, no network) for installed-artifact checks:

- ``--selftest`` / ``--self-test`` — imports the bundle's dependencies, core
  modules and the GUI module, builds a DICOMDIR from a tiny synthetic DICOM
  study in a temp folder, prints the result and exits 0/1 (``mia/selftest.py``).
- ``--version`` — prints the app version and exits 0.
"""

import sys


def _gui_imports() -> None:
    # Import (don't start) the GUI so a bundle missing Tk or a GUI module fails.
    from mia.gui import app  # noqa: F401


def main(argv=None) -> int:
    argv = sys.argv if argv is None else argv
    from mia import selftest

    if selftest.wants_selftest(argv):
        return selftest.run(extra_imports=_gui_imports)
    if "--version" in argv[1:]:
        from mia import __version__
        print(f"MIA Toolkit {__version__}")
        return 0
    from mia.gui.app import main as gui_main
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
