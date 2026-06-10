import os

import pytest

from mia.core import common, deliver
from mia.core.common import Cancelled
from tests.helpers import CancelNow


@pytest.fixture(autouse=True)
def _quiet_verbose():
    """Verbose is ON in production, but the copy/native tests want a known,
    quiet baseline (no per-file debug stream, no ditto -v capture). Pin it off
    and restore — tests that exercise verbose set it explicitly."""
    orig = common.is_verbose()
    common.set_verbose(False)
    yield
    common.set_verbose(orig)


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


# The deterministic copy/verify/resume tests force prefer_native=False so they
# exercise our in-process parallel pass on every platform (the native tool,
# when present, would copy first and leave the verify pass nothing to do —
# covered separately by test_native_path_leaves_all_present).

def test_copy_tree_verified_copies_all(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    files = _tree(str(src))
    result = deliver.copy_tree_verified(str(src), str(dst), prefer_native=False)

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
    deliver.copy_tree_verified(str(src), str(dst), prefer_native=False)

    # Delete one destination file; a re-run should restore just that one.
    os.remove(dst / "a.txt")
    result = deliver.copy_tree_verified(str(src), str(dst), prefer_native=False)
    assert result.files_copied == 1
    assert result.files_skipped == 2
    assert (dst / "a.txt").exists()


def test_thorough_detects_and_repairs_corruption(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(str(src))
    deliver.copy_tree_verified(str(src), str(dst), prefer_native=False)

    # Corrupt a dest file WITHOUT changing its size.
    target = dst / "sub" / "b.bin"
    size = target.stat().st_size
    with open(target, "wb") as f:
        f.write(b"\xff" * size)

    # Non-thorough (size-only) can't see it; thorough recopies it.
    quick = deliver.copy_tree_verified(str(src), str(dst), prefer_native=False)
    assert quick.files_copied == 0  # sizes match -> skipped

    thorough = deliver.copy_tree_verified(str(src), str(dst), thorough=True,
                                          prefer_native=False)
    assert thorough.files_copied == 1
    with open(src / "sub" / "b.bin", "rb") as a, open(target, "rb") as b:
        assert a.read() == b.read()


def test_native_path_leaves_all_present(tmp_path):
    # With the native fast-path on (default), whichever copier runs, every file
    # must end up present, verified, and byte-identical.
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    files = _tree(str(src))
    result = deliver.copy_tree_verified(str(src), str(dst))  # prefer_native=True
    assert result.verified and result.failed == 0
    assert result.files_copied + result.files_skipped == len(files)
    for rel, data in files:
        with open(dst / rel, "rb") as f:
            assert f.read() == data


def test_native_copy_emits_indeterminate_progress(tmp_path, monkeypatch):
    # While the OS tool runs we can't honestly count files (free space jitters
    # on USB), so the native phase must emit an *indeterminate* "working" tick —
    # an animated bar with no fake ETA — so a long USB copy doesn't look frozen.
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(str(src))

    class FakeProc:
        def __init__(self):
            self._polls = 0
            self.returncode = 0

        def poll(self):
            self._polls += 1
            return None if self._polls < 3 else 0  # alive for 2 iterations

    monkeypatch.setattr(deliver.shutil, "which", lambda _c: "/bin/true")
    monkeypatch.setattr(deliver.subprocess, "Popen",
                        lambda *a, **k: FakeProc())
    monkeypatch.setattr(deliver.time, "sleep", lambda _s: None)

    events = []
    deliver.copy_tree_verified(str(src), str(dst), prefer_native=True,
                               progress=events.append)
    native = [e for e in events if e.phase == "copy" and e.indeterminate]
    assert native, "native phase emitted no indeterminate working tick"
    # Honest: no made-up percentage/ETA during the opaque native copy.
    assert all(e.done == 0 and e.eta == 0 for e in native)


def test_ditto_gets_dash_v_and_streams_to_debug_when_verbose(tmp_path,
                                                             monkeypatch):
    # With the verbose technical log on, ditto runs with -v and its per-item
    # stderr stream is forwarded as kind="debug" notes — so a slow USB copy
    # shows *which* file it's on.
    from mia.core import common

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(str(src))

    seen = {}

    class FakeProc:
        def __init__(self, cmd):
            self._polls = 0
            self.returncode = 0
            self.stderr = iter([">>> Copying a.txt\n", ">>> Copying b.bin\n"])

        def poll(self):
            self._polls += 1
            return None if self._polls < 3 else 0

    def fake_popen(cmd, **_k):
        seen["cmd"] = cmd
        return FakeProc(cmd)

    monkeypatch.setattr(deliver.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(deliver.shutil, "which", lambda _c: "/usr/bin/ditto")
    monkeypatch.setattr(deliver.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(deliver.time, "sleep", lambda _s: None)

    common.set_verbose(True)
    try:
        events = []
        deliver.copy_tree_verified(str(src), str(dst), prefer_native=True,
                                   progress=events.append)
    finally:
        common.set_verbose(False)

    assert seen["cmd"][:2] == ["ditto", "-v"]
    debug_notes = [e.note for e in events if e.kind == "debug" and e.note]
    assert any("Copying a.txt" in n for n in debug_notes)
    assert any("Copying b.bin" in n for n in debug_notes)


def test_ditto_no_dash_v_when_not_verbose(tmp_path, monkeypatch):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(str(src))
    seen = {}

    class FakeProc:
        def __init__(self):
            self._polls = 0
            self.returncode = 0

        def poll(self):
            self._polls += 1
            return None if self._polls < 2 else 0

    monkeypatch.setattr(deliver.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(deliver.shutil, "which", lambda _c: "/usr/bin/ditto")
    monkeypatch.setattr(deliver.subprocess, "Popen",
                        lambda cmd, **_k: (seen.__setitem__("cmd", cmd)
                                           or FakeProc()))
    monkeypatch.setattr(deliver.time, "sleep", lambda _s: None)

    deliver.copy_tree_verified(str(src), str(dst), prefer_native=True,
                               progress=lambda _p: None)
    assert "-v" not in seen["cmd"]


def test_copy_creates_nested_dirs_without_upfront_precreate(tmp_path):
    # We dropped the upfront dest-tree mkdir storm (minutes of dead time on
    # USB). The verify/fill pass must still create each file's parent lazily,
    # so a deep tree copies correctly with prefer_native off.
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    files = _tree(str(src))  # includes sub/deep/c.dat
    result = deliver.copy_tree_verified(str(src), str(dst), prefer_native=False)
    assert result.failed == 0
    assert (dst / "sub" / "deep" / "c.dat").exists()
    assert result.files_copied == len(files)


def test_verbose_gates_debug_emits(tmp_path):
    from mia.core import common

    src = tmp_path / "src"
    _tree(str(src))

    common.set_verbose(False)
    try:
        quiet = []
        deliver.copy_tree_verified(str(src), str(tmp_path / "a"),
                                   prefer_native=False, progress=quiet.append)
        assert not [e for e in quiet if e.kind == "debug"]

        common.set_verbose(True)
        loud = []
        deliver.copy_tree_verified(str(src), str(tmp_path / "b"),
                                   prefer_native=False, progress=loud.append)
        assert [e for e in loud if e.kind == "debug"]  # walk/verify timings
    finally:
        common.set_verbose(False)


def test_verify_sample_detects_corruption_in_sampled_files(tmp_path):
    # A same-size content corruption is invisible to size-only verification but
    # caught when the file is in the SHA-256 sample. verify_sample >= total puts
    # every file in the sample, so the corrupted one is detected and recopied.
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(str(src))
    deliver.copy_tree_verified(str(src), str(dst), prefer_native=False)

    target = dst / "sub" / "b.bin"
    size = target.stat().st_size
    with open(target, "wb") as f:
        f.write(b"\xff" * size)                 # same size, wrong bytes

    res = deliver.copy_tree_verified(str(src), str(dst), prefer_native=False,
                                     verify_sample=999)
    assert res.files_copied == 1                 # the corrupt file was repaired
    assert res.content_verified == 3             # all 3 files sampled
    with open(src / "sub" / "b.bin", "rb") as a, open(target, "rb") as b:
        assert a.read() == b.read()


def test_verify_sample_zero_is_size_only(tmp_path):
    # The default (no sample) can't see a same-size corruption — proving the
    # sample is what adds the content check, not the size pass.
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(str(src))
    deliver.copy_tree_verified(str(src), str(dst), prefer_native=False)
    target = dst / "sub" / "b.bin"
    size = target.stat().st_size                 # read size BEFORE truncating
    with open(target, "wb") as f:
        f.write(b"\xff" * size)                  # same size, wrong bytes

    res = deliver.copy_tree_verified(str(src), str(dst), prefer_native=False)
    assert res.files_copied == 0                 # size matched -> not detected
    assert res.content_verified == 0


def test_verify_sample_caps_at_file_count(tmp_path, monkeypatch):
    # The sample size is min(verify_sample, total); random.sample is asked for a
    # valid count, and content_verified reports how many were checked.
    src = tmp_path / "src"
    _tree(str(src))  # 3 files
    asked = {}
    real_sample = deliver.random.sample

    def spy(pop, k):
        asked["k"] = k
        return real_sample(pop, k)

    monkeypatch.setattr(deliver.random, "sample", spy)
    res = deliver.copy_tree_verified(str(src), str(tmp_path / "d"),
                                     prefer_native=False, verify_sample=2)
    assert asked["k"] == 2
    assert res.content_verified == 2


def test_groups_emit_ordered_milestones_and_copy_all(tmp_path):
    # groups announce per-group info milestones (in order) while every file is
    # still copied and the overall bar counts them all.
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _tree(str(src))  # a.txt, sub/b.bin, sub/deep/c.dat
    # Pass group paths through a symlinked alias of src (realpath-divergent,
    # like macOS /var vs /private/var) to exercise the path normalization.
    alias = tmp_path / "alias"
    try:
        os.symlink(str(src), str(alias))
        base = str(alias)
    except (OSError, NotImplementedError):
        base = str(src)
    a = os.path.join(base, "a.txt")
    b = os.path.join(base, "sub", "b.bin")
    # c.dat deliberately left out of the groups -> trailing unlabeled group.
    groups = [("Study 1 of 2", [a]), ("Study 2 of 2", [b])]

    events = []
    res = deliver.copy_tree_verified(str(src), str(dst), prefer_native=False,
                                     groups=groups, progress=events.append)
    assert res.files_copied == 3 and res.failed == 0
    for rel in ("a.txt", "sub/b.bin", "sub/deep/c.dat"):
        assert (dst / rel).exists()                  # leftover copied too
    milestones = [e.note for e in events
                  if e.kind == "info" and e.phase == "copy"]
    assert milestones == ["Study 1 of 2", "Study 2 of 2"]   # ordered, no tail

    # Determinate ticks inside a labeled group carry per-group image counts so
    # the UI can say "image k of N", with group_done never exceeding the total.
    grouped = [e for e in events if e.kind == "progress"
               and e.phase == "copy" and e.group_total]
    assert grouped and all(0 < e.group_done <= e.group_total for e in grouped)


def test_groups_none_is_unchanged_flat_copy(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    files = _tree(str(src))
    events = []
    res = deliver.copy_tree_verified(str(src), str(dst), prefer_native=False,
                                     progress=events.append)
    assert res.files_copied == len(files)
    assert not [e for e in events if e.kind == "info" and e.phase == "copy"]


def test_verbose_emits_per_file_copy_stream(tmp_path):
    src = tmp_path / "src"
    _tree(str(src))
    common.set_verbose(True)
    try:
        events = []
        deliver.copy_tree_verified(str(src), str(tmp_path / "d"),
                                   prefer_native=False, progress=events.append)
    finally:
        common.set_verbose(False)
    stream = [e.note for e in events if e.kind == "debug"
              and e.note and e.note.startswith("copying ")]
    assert len(stream) == 3                            # one per copied file


def test_cancellation(tmp_path):
    src = tmp_path / "src"
    _tree(str(src))
    with pytest.raises(Cancelled):
        deliver.copy_tree_verified(str(src), str(tmp_path / "dst"),
                                   prefer_native=False, cancel=CancelNow())


def test_free_space_and_dir_size(tmp_path):
    src = tmp_path / "src"
    _tree(str(src))
    assert deliver.dir_size(str(src)) == 5 + 400 + 5000
    # Free space on an existing path is a positive number.
    assert deliver.free_space(str(tmp_path)) > 0
    # Also works for a not-yet-existing child (uses nearest existing parent).
    assert deliver.free_space(str(tmp_path / "does" / "not" / "exist")) > 0
