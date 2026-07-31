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


if __name__ == "__main__":
    unittest.main()
