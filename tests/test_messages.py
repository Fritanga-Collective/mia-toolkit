import errno

from mia.core.common import Progress
from mia.gui.messages import Presenter, exception_detail, humanize_exception


def test_info_note_shown_in_both():
    plain, tech = Presenter().feed(
        Progress(0, 0, note="Indexing disc...", kind="info"))
    assert plain == "Indexing disc..."
    assert tech == "Indexing disc..."


def test_retry_is_friendly_but_keeps_raw_in_technical():
    plain, tech = Presenter().feed(
        Progress(5, 10, note="[5/10] IM5 (recovered with dd)", kind="retry"))
    assert "Recovered" in plain
    assert "dd" in tech            # raw note preserved for the audit stream


def test_fail_is_friendly_but_keeps_raw_in_technical():
    plain, tech = Presenter().feed(
        Progress(6, 10, note="[6/10] IM6 (bad sector)", kind="fail"))
    assert "Could not read" in plain
    assert "bad sector" in tech


def test_progress_ticks_are_throttled():
    t = {"v": 0.0}
    p = Presenter(clock=lambda: t["v"], interval=1.0)

    plain1, tech1 = p.feed(Progress(1, 100, rate=10, eta=9, phase="copy"))
    assert plain1 is not None and tech1 is not None       # first tick emits

    plain2, tech2 = p.feed(Progress(2, 100, phase="copy"))
    assert plain2 is None and tech2 is None               # too soon -> dropped

    t["v"] = 1.5
    plain3, _ = p.feed(Progress(3, 100, phase="copy"))
    assert plain3 is not None                              # interval elapsed

    t["v"] = 1.6
    plainf, _ = p.feed(Progress(100, 100, phase="copy"))
    assert plainf is not None                              # final tick always emits


def test_plain_tick_wording_by_phase():
    t = {"v": 0.0}
    p = Presenter(clock=lambda: t["v"], interval=1.0)
    assert "Copying" in p.feed(Progress(2, 10, phase="copy"))[0]
    t["v"] = 2.0
    assert "Scanning" in p.feed(Progress(3, 10, phase="scan"))[0]
    t["v"] = 4.0
    assert "Indexing" in p.feed(Progress(4, 10, phase="index"))[0]


def test_humanize_exception_maps_common_errors():
    assert "permission" in humanize_exception(PermissionError()).lower()
    assert humanize_exception(FileNotFoundError())
    nospace = OSError()
    nospace.errno = errno.ENOSPC
    assert "full" in humanize_exception(nospace).lower()
    assert "went wrong" in humanize_exception(ValueError("x")).lower()


def test_exception_detail_contains_traceback():
    try:
        raise ValueError("boom")
    except ValueError as e:
        detail = exception_detail(e)
    assert "ValueError" in detail and "boom" in detail
