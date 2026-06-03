"""The wizard's auto-managed project: one folder that holds everything.

The user never picks working paths in the guided flow — the wizard keeps ripped
discs, the inventory, and the built archive under a single project root
(``~/Documents/MedicalArchive`` by default). Only the USB destination is chosen,
at delivery time.
"""

from __future__ import annotations

import os

from mia.core import deliver


class Project:
    def __init__(self, root: str = "") -> None:
        self.root = os.path.abspath(
            os.path.expanduser(root or "~/Documents/MedicalArchive"))

    # Derived locations
    @property
    def raw_discs_dir(self) -> str:
        return os.path.join(self.root, "raw_discs")

    @property
    def archive_dir(self) -> str:
        return os.path.join(self.root, "Archive")

    @property
    def inventory_path(self) -> str:
        return os.path.join(self.root, "dicom_inventory.xlsx")

    def ensure_dirs(self) -> None:
        os.makedirs(self.raw_discs_dir, exist_ok=True)

    # State queries
    def discs(self) -> list[str]:
        d = self.raw_discs_dir
        if not os.path.isdir(d):
            return []
        return sorted(
            os.path.join(d, e) for e in os.listdir(d)
            if e.startswith("disc_") and os.path.isdir(os.path.join(d, e)))

    def disc_count(self) -> int:
        return len(self.discs())

    def has_discs(self) -> bool:
        return self.disc_count() > 0

    def has_archive(self) -> bool:
        return os.path.exists(os.path.join(self.archive_dir, "DICOMDIR"))

    # Space helpers (bytes)
    def free_space(self) -> int:
        return deliver.free_space(self.root)

    def raw_size(self) -> int:
        return deliver.dir_size(self.raw_discs_dir)

    def relocate(self, new_root: str, *, progress=None, cancel=None):
        """Point the project at a new drive, moving existing data if present.

        Returns a DeliverResult when data was moved, else None.
        """
        new_root = os.path.abspath(os.path.expanduser(new_root))
        result = None
        if os.path.isdir(self.raw_discs_dir) and self.has_discs():
            result = deliver.copy_tree_verified(
                self.raw_discs_dir, os.path.join(new_root, "raw_discs"),
                progress=progress, cancel=cancel)
        self.root = new_root
        self.ensure_dirs()
        return result
