#!/usr/bin/env python3
"""Backward-compatible CLI shim. See mia_core/dicomdir.py for the implementation.

Usage is unchanged:
    python3 build_dicomdir.py
    python3 build_dicomdir.py /custom/source -o /Volumes/USB/Archive
"""
import sys

from mia_core.dicomdir import main

if __name__ == "__main__":
    sys.exit(main())
