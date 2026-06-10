"""The Add-documents wizard step's per-row UI: unchecking a file disables its
embed-target dropdown and shows a "Skip this file" label; re-checking restores
the prior choice. Needs a real Tk; skipped without a display."""

from types import SimpleNamespace

import pytest

pytest.importorskip("tkinter")

from mia.gui.wizard.steps import AddDocumentsStep  # noqa: E402
from tests.helpers import new_tk_root_or_skip  # noqa: E402


@pytest.fixture
def step():
    root = new_tk_root_or_skip()
    wizard = SimpleNamespace(project=SimpleNamespace(), inventory_result=None,
                             documents_plan=[])
    s = AddDocumentsStep(root, wizard)
    yield s
    root.destroy()


def test_uncheck_disables_dropdown_with_skip_label(step):
    # Give it a study to embed into so the dropdown is normally enabled.
    step._refs = [SimpleNamespace(study_uid="s1", label="CT CHEST 2021")]
    step._add_row("/tmp/report.pdf", default_study=None, found=True)
    row = step._rows[-1]
    combo = row["combo"]
    assert str(combo.cget("state")) == "readonly"   # enabled while included
    included_label = combo.get()

    row["include"].set(False)
    row["toggle"]()
    assert str(combo.cget("state")) == "disabled"
    assert combo.get() == step._skip_label()

    row["include"].set(True)
    row["toggle"]()
    assert str(combo.cget("state")) == "readonly"   # restored
    assert combo.get() == included_label            # prior choice preserved


def test_unchecked_row_is_left_out_of_the_plan(step):
    step._add_row("/tmp/a.pdf", default_study=None, found=True)
    step._add_row("/tmp/b.pdf", default_study=None, found=True)
    keep, drop = step._rows
    drop["include"].set(False)
    drop["toggle"]()

    step.on_leave()
    paths = [d["path"] for d in step.wizard.documents_plan]
    assert paths == ["/tmp/a.pdf"]                  # only the checked row
