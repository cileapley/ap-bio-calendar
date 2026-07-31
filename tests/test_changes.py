import unittest

import changes


def calendar(*entries):
    """A minimal calendar.json shaped document containing one block.

    Each argument is a dict overriding the defaults below, so a test only
    states the fields it cares about.
    """
    built = []
    for e in entries:
        entry = {"id": None, "title": "T", "kind": "topic", "skill": None,
                 "notes": None, "link": None, "periods": 1,
                 "start": "2026-09-15", "end": "2026-09-15",
                 "dates": ["2026-09-15"]}
        entry.update(e)
        built.append(entry)
    return {"blocks": [{"id": "unit-2", "unit": 2, "title": "Cells",
                        "entries": built}]}


class TestNoChange(unittest.TestCase):
    def test_identical_calendars_produce_nothing(self):
        cal = calendar({"id": "2.7", "periods": 3})
        self.assertEqual(changes.diff(cal, cal), [])

    def test_unrelated_fields_are_ignored(self):
        # `skill` and `notes` are not part of the join contract.
        old = calendar({"id": "2.7", "skill": "4.A"})
        new = calendar({"id": "2.7", "skill": "9.Z", "notes": "hi"})
        self.assertEqual(changes.diff(old, new), [])


class TestResize(unittest.TestCase):
    def test_shrinking_reports_the_lost_indices(self):
        old = calendar({"id": "INV-4", "kind": "lab", "periods": 3,
                        "start": "2026-09-15", "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "kind": "lab", "periods": 2,
                        "start": "2026-09-15", "end": "2026-09-16"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.entry_id, "INV-4")
        self.assertIn("RESIZED", delta.changes)
        self.assertEqual(delta.lost_day_indices, (3,))

    def test_shrinking_by_two_reports_both_indices(self):
        old = calendar({"id": "INV-4", "periods": 3, "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "periods": 1, "end": "2026-09-15"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.lost_day_indices, (2, 3))

    def test_growing_loses_no_days(self):
        old = calendar({"id": "INV-4", "periods": 2, "end": "2026-09-16"})
        new = calendar({"id": "INV-4", "periods": 3, "end": "2026-09-17"})
        (delta,) = changes.diff(old, new)
        self.assertIn("RESIZED", delta.changes)
        self.assertEqual(delta.lost_day_indices, ())

    def test_a_pure_resize_is_not_also_reported_as_a_move(self):
        # Shrinking moves the end date as a direct consequence. Reporting that
        # as a move too would flag every resized entry twice.
        old = calendar({"id": "INV-4", "periods": 3,
                        "start": "2026-09-15", "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "periods": 2,
                        "start": "2026-09-15", "end": "2026-09-16"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.changes, ("RESIZED",))


class TestMove(unittest.TestCase):
    def test_changed_start_is_a_move(self):
        old = calendar({"id": "2.7", "start": "2026-09-15", "end": "2026-09-15"})
        new = calendar({"id": "2.7", "start": "2026-09-16", "end": "2026-09-16"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.changes, ("MOVED",))

    def test_same_length_sliding_end_is_a_move(self):
        # A holiday inserted mid-entry keeps the length but pushes the end.
        old = calendar({"id": "2.7", "periods": 2,
                        "start": "2026-09-15", "end": "2026-09-16"})
        new = calendar({"id": "2.7", "periods": 2,
                        "start": "2026-09-15", "end": "2026-09-17"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.changes, ("MOVED",))

    def test_an_entry_can_move_and_resize_in_one_delta(self):
        old = calendar({"id": "2.7", "periods": 3,
                        "start": "2026-09-15", "end": "2026-09-17"})
        new = calendar({"id": "2.7", "periods": 2,
                        "start": "2026-09-21", "end": "2026-09-22"})
        deltas = changes.diff(old, new)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(set(deltas[0].changes), {"MOVED", "RESIZED"})


class TestAddRemove(unittest.TestCase):
    def test_new_id_is_added(self):
        (delta,) = changes.diff(calendar(), calendar({"id": "2.7"}))
        self.assertEqual(delta.changes, ("ADDED",))
        self.assertIsNone(delta.old)
        self.assertIsNotNone(delta.new)

    def test_vanished_id_is_removed(self):
        (delta,) = changes.diff(calendar({"id": "2.7"}), calendar())
        self.assertEqual(delta.changes, ("REMOVED",))
        self.assertIsNone(delta.new)
        self.assertIsNotNone(delta.old)

    def test_removed_entry_keeps_its_old_title(self):
        old = calendar({"id": "2.7", "title": "Tonicity"})
        (delta,) = changes.diff(old, calendar())
        self.assertEqual(delta.title, "Tonicity")


class TestRetitle(unittest.TestCase):
    def test_changed_title_is_reported(self):
        old = calendar({"id": "2.7", "title": "Tonicity"})
        new = calendar({"id": "2.7", "title": "Tonicity and Osmoregulation"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.changes, ("RETITLED",))
        self.assertEqual(delta.title, "Tonicity and Osmoregulation")


class TestIdlessEntries(unittest.TestCase):
    def test_idless_entry_matches_on_block_and_title(self):
        # Four real entries carry no id: the opening block and the two `fill`
        # review blocks. Matching them by position would report the whole year
        # as changed the moment an entry is inserted above them.
        cal = calendar({"id": None, "title": "Post-exam project"})
        self.assertEqual(changes.diff(cal, cal), [])

    def test_idless_entry_still_reports_a_move(self):
        old = calendar({"id": None, "title": "Post-exam project",
                        "start": "2027-05-04"})
        new = calendar({"id": None, "title": "Post-exam project",
                        "start": "2027-05-05"})
        (delta,) = changes.diff(old, new)
        self.assertEqual(delta.entry_id, "unit-2:Post-exam project")
        self.assertEqual(delta.changes, ("MOVED",))


class TestOrdering(unittest.TestCase):
    def test_deltas_come_back_most_consequential_first(self):
        old = calendar({"id": "gone"}, {"id": "shrink", "periods": 3,
                                        "end": "2026-09-17"},
                       {"id": "slide", "start": "2026-09-15"},
                       {"id": "rename", "title": "Old"})
        new = calendar({"id": "shrink", "periods": 2, "end": "2026-09-16"},
                       {"id": "slide", "start": "2026-09-20",
                        "end": "2026-09-20"},
                       {"id": "rename", "title": "New"},
                       {"id": "fresh"})
        order = [d.changes[0] for d in changes.diff(old, new)]
        self.assertEqual(order, ["REMOVED", "RESIZED", "MOVED",
                                 "ADDED", "RETITLED"])


class TestRenderText(unittest.TestCase):
    def _deltas(self):
        old = calendar({"id": "INV-4", "kind": "lab",
                        "title": "Investigation 4", "periods": 3,
                        "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "kind": "lab",
                        "title": "Investigation 4", "periods": 2,
                        "end": "2026-09-16"})
        return changes.diff(old, new)

    def test_empty_input_says_nothing_changed(self):
        text = changes.render_text([])
        self.assertIn("No changes", text)

    def test_groups_under_a_severity_heading(self):
        self.assertIn("RESIZED", changes.render_text(self._deltas()))

    def test_shows_the_period_transition(self):
        self.assertIn("3 days -> 2", changes.render_text(self._deltas()))

    def test_names_the_orphaned_key_as_a_hint(self):
        # The JSON stays convention-free; the human summary spells the key out
        # because "orphans INV-4-d3" is what tells you which file to delete.
        self.assertIn("INV-4-d3", changes.render_text(self._deltas()))

    def test_reports_what_did_not_change(self):
        text = changes.render_text(self._deltas())
        self.assertIn("Nothing", text)

    def test_added_and_removed_render_without_touching_the_missing_side(self):
        # An ADDED delta has old=None and a REMOVED delta has new=None, so
        # every branch must read only the side that exists. Structural safety
        # today; this makes a regression fail instead of crashing on real data.
        added = changes.diff(calendar(), calendar({"id": "2.7"}))
        removed = changes.diff(calendar({"id": "2.7"}), calendar())
        self.assertIn("ADDED", changes.render_text(added))
        self.assertIn("REMOVED", changes.render_text(removed))

    def test_groups_appear_in_severity_order(self):
        # Headings must print most-consequential-first. Iterating in insertion
        # order instead would pass every other test in this class.
        old = calendar({"id": "gone"}, {"id": "rename", "title": "Old"})
        new = calendar({"id": "rename", "title": "New"}, {"id": "fresh"})
        text = changes.render_text(changes.diff(old, new))
        self.assertLess(text.index("REMOVED"), text.index("ADDED"))
        self.assertLess(text.index("ADDED"), text.index("RETITLED"))

    def test_header_counts_distinct_entries_not_the_sum_of_groups(self):
        # One entry that both moved and resized appears under two headings.
        # The header states how many entries actually changed.
        old = calendar({"id": "2.7", "periods": 3,
                        "start": "2026-09-15", "end": "2026-09-17"})
        new = calendar({"id": "2.7", "periods": 2,
                        "start": "2026-09-21", "end": "2026-09-22"})
        text = changes.render_text(changes.diff(old, new))
        self.assertIn("1 entry changed", text)
        self.assertIn("RESIZED", text)
        self.assertIn("MOVED", text)


class TestRenderJson(unittest.TestCase):
    def _deltas(self):
        old = calendar({"id": "INV-4", "periods": 3, "end": "2026-09-17"})
        new = calendar({"id": "INV-4", "periods": 2, "end": "2026-09-16"})
        return changes.diff(old, new)

    def test_output_is_valid_json_with_a_stable_shape(self):
        import json
        payload = json.loads(changes.render_json(self._deltas()))
        self.assertIn("changes", payload)
        self.assertIn("counts", payload)
        self.assertEqual(payload["counts"]["RESIZED"], 1)

    def test_lost_days_are_raw_integers_not_formatted_keys(self):
        # The {id}-d{n} format is this project's suggestion to the lesson-plan
        # workspace, not their published contract. Baking a guess at another
        # project's key format into this output would make the two disagree
        # silently the moment they diverge.
        import json
        payload = json.loads(changes.render_json(self._deltas()))
        entry = payload["changes"][0]
        self.assertEqual(entry["lost_day_indices"], [3])
        self.assertNotIn("INV-4-d3", changes.render_json(self._deltas()))

    def test_empty_input_still_produces_a_valid_document(self):
        import json
        payload = json.loads(changes.render_json([]))
        self.assertEqual(payload["changes"], [])
        self.assertEqual(payload["counts"], {})

    def test_counts_tally_change_types_not_entries(self):
        # Deliberate: counts is a category tally, so a two-label delta
        # increments two counters while `changes` holds one record.
        import json
        old = calendar({"id": "2.7", "periods": 3,
                        "start": "2026-09-15", "end": "2026-09-17"})
        new = calendar({"id": "2.7", "periods": 2,
                        "start": "2026-09-21", "end": "2026-09-22"})
        payload = json.loads(changes.render_json(changes.diff(old, new)))
        self.assertEqual(payload["counts"], {"RESIZED": 1, "MOVED": 1})
        self.assertEqual(len(payload["changes"]), 1)


class TestBaseline(unittest.TestCase):
    def test_missing_baseline_is_not_an_error(self):
        # Before the first commit there is nothing to compare against. That is
        # a fact about the repository, not a failure.
        text, code = changes.report(None, {"blocks": []})
        self.assertEqual(code, 0)
        self.assertIn("No git baseline", text)

    def test_present_baseline_produces_a_report(self):
        old = calendar({"id": "2.7", "periods": 2, "end": "2026-09-16"})
        new = calendar({"id": "2.7", "periods": 1, "end": "2026-09-15"})
        text, code = changes.report(old, new)
        self.assertEqual(code, 0)
        self.assertIn("RESIZED", text)

    def test_identical_calendars_exit_zero(self):
        cal = calendar({"id": "2.7"})
        text, code = changes.report(cal, cal)
        self.assertEqual(code, 0)
        self.assertIn("No changes", text)


if __name__ == "__main__":
    unittest.main()
