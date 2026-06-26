#!/usr/bin/env python3
"""Backward-compatible CLI shim. See mia_core/ripper.py for the implementation.

Usage is unchanged:
    python3 rip_cd.py                 # auto-detect
    python3 rip_cd.py /Volumes/CD -o ~/Imaging/raw_discs
"""
import sys

from mia_core.ripper import main

if __name__ == "__main__":
    sys.exit(main())
