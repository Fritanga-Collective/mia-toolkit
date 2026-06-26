#!/usr/bin/env python3
"""Backward-compatible CLI shim. See mia_core/inventory.py for the implementation.

Usage is unchanged:
    python3 dicom_inventory.py /path/to/raw_discs
    python3 dicom_inventory.py /path/to/raw_discs -o my_inventory.xlsx
"""
import sys

from mia_core.inventory import main

if __name__ == "__main__":
    sys.exit(main())
