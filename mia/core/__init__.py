"""Wrapped worker logic for the toolkit.

These modules preserve the algorithms of the original standalone scripts
(``rip_cd.py``, ``dicom_inventory.py``, ``build_dicomdir.py``) verbatim. The
only change is the I/O boundary: instead of printing and calling ``sys.exit``,
each worker accepts an optional progress callback and cancel token and returns
a structured result object. Thin CLI shims reproduce the original
command-line behavior on top of these workers.
"""
