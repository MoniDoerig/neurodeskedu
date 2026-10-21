import copy
import unittest

from merge_notebook_outputs import merge_outputs


class MergeOutputTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "metadata": {"nd_review_id": "current", "widgets": {"old": "state"}},
            "cells": [
                {"cell_type": "markdown", "source": ["# Current title\n", "Current author and screenshot.png"]},
                {"cell_type": "code", "source": ["print(1)\n"], "id": "current-cell",
                 "metadata": {"tags": ["hide-input"]}, "outputs": [], "execution_count": None},
            ],
        }
        self.cached = {
            "metadata": {"nd_review_id": "obsolete", "widgets": {"new": "widget state"}},
            "cells": [
                {"cell_type": "markdown", "source": "# Old title\nobsolete.jpg"},
                {"cell_type": "code", "source": "print(1)\n", "id": "cached-cell",
                 "metadata": {}, "execution_count": 2,
                 "outputs": [{"output_type": "stream", "name": "stdout", "text": "1\n"}]},
            ],
        }

    def test_preserves_current_tutorial_and_cell_metadata_with_matching_outputs(self):
        before = copy.deepcopy(self.source)
        self.assertTrue(merge_outputs(self.source, self.cached))
        self.assertEqual(self.source["cells"][0], before["cells"][0])
        self.assertEqual(self.source["metadata"]["nd_review_id"], "current")
        self.assertEqual(self.source["cells"][1]["metadata"], {"tags": ["hide-input"]})
        self.assertEqual(self.source["cells"][1]["id"], "current-cell")
        self.assertEqual(self.source["cells"][1]["outputs"], self.cached["cells"][1]["outputs"])
        self.assertEqual(self.source["cells"][1]["execution_count"], 2)
        self.assertEqual(self.source["metadata"]["widgets"], {"new": "widget state"})

    def test_changed_or_added_code_keeps_current_outputs_and_widgets(self):
        for change in ("changed", "added"):
            with self.subTest(change=change):
                source = copy.deepcopy(self.source)
                if change == "changed":
                    source["cells"][1]["source"] = "print(2)"
                else:
                    source["cells"].append(copy.deepcopy(source["cells"][1]))
                before = copy.deepcopy(source)
                self.assertFalse(merge_outputs(source, self.cached))
                self.assertEqual(source, before)

    def test_removes_stale_widget_state_when_matching_result_has_no_widgets(self):
        self.cached["metadata"].pop("widgets")
        self.assertTrue(merge_outputs(self.source, self.cached))
        self.assertNotIn("widgets", self.source["metadata"])


if __name__ == "__main__":
    unittest.main()
