import os

import pytest

from mia.core import deliver
from mia.core.common import Cancelled
from tests.conftest import CancelNow


def _tree(root):
    """Make a small src tree; return list of (relpath, content)."""
    files = [
        ("a.txt", b"alpha"),
        ("sub/b.bin", b"\x00\x01\x02\x03" * 100),
        ("sub/deep/c.dat", b"c" * 5000),
    ]
    for rel, data in files:
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
    return files


def test_copy_tree_verified_copies_all(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    files = _tree(str(src))
    result = deliver.copy_tree_verified(str(src), str(dst))

    assert result.total_files == len(files)
    assert result.files_copied == len(files)
    assert result.failed == 0
    assert result.verified
    for rel, data in files:
        with open(dst / rel, "rb") as f:
            assert f.read() == data


def test_resume_skips_existing_and_restores_missing(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(str(src))
    deliver.copy_tree_verified(str(src), str(dst))

    # Delete one destination file; a re-run should restore just that one.
    os.remove(dst / "a.txt")
    result = deliver.copy_tree_verified(str(src), str(dst))
    assert result.files_copied == 1
    assert result.files_skipped == 2
    assert (dst / "a.txt").exists()


def test_thorough_detects_and_repairs_corruption(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(str(src))
    deliver.copy_tree_verified(str(src), str(dst))

    # Corrupt a dest file WITHOUT changing its size.
    target = dst / "sub" / "b.bin"
    size = target.stat().st_size
    with open(target, "wb") as f:
        f.write(b"\xff" * size)

    # Non-thorough (size-only) can't see it; thorough recopies it.
    quick = deliver.copy_tree_verified(str(src), str(dst))
    assert quick.files_copied == 0  # sizes match -> skipped

    thorough = deliver.copy_tree_verified(str(src), str(dst), thorough=True)
    assert thorough.files_copied == 1
    with open(src / "sub" / "b.bin", "rb") as a, open(target, "rb") as b:
        assert a.read() == b.read()


def test_cancellation(tmp_path):
    src = tmp_path / "src"
    _tree(str(src))
    with pytest.raises(Cancelled):
        deliver.copy_tree_verified(str(src), str(tmp_path / "dst"),
                                   cancel=CancelNow())


def test_free_space_and_dir_size(tmp_path):
    src = tmp_path / "src"
    _tree(str(src))
    assert deliver.dir_size(str(src)) == 5 + 400 + 5000
    # Free space on an existing path is a positive number.
    assert deliver.free_space(str(tmp_path)) > 0
    # Also works for a not-yet-existing child (uses nearest existing parent).
    assert deliver.free_space(str(tmp_path / "does" / "not" / "exist")) > 0
