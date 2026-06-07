"""Medical Imaging Archive Toolkit.

A small toolkit for consolidating a stack of hospital imaging CDs into a
single, standards-compliant DICOM archive a radiologist can ingest.

The ``mia.core`` package contains the wrapped worker logic (ripping discs,
building an inventory, building a unified DICOMDIR). Each worker is UI- and
transport-agnostic: it reports progress through a callback and observes an
optional cancel token, so the same code drives both the command-line shims
and (later) the GUI.
"""

__version__ = "0.1.8"
