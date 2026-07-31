import unittest
from datetime import date, timedelta

import prep


def instructional(start, end, skip=()):
    """Weekdays from start to end inclusive, minus any dates in skip."""
    days, day = [], start
    while day <= end:
        if day.weekday() < 5 and day not in skip:
            days.append(day)
        day += timedelta(days=1)
    return days


def lab_block(lab_id, lab_date, prep_spec):
    return [{
        "unit": 3,
        "entries": [{
            "id": lab_id,
            "title": "Investigation X — Test Lab",
            "kind": "lab",
            "dates": [lab_date],
            "prep": prep_spec,
        }],
    }]


class TestSnapBack(unittest.TestCase):
    def setUp(self):
        self.days = set(instructional(date(2026, 8, 12), date(2026, 12, 18)))

    def test_instructional_day_snaps_to_itself(self):
        self.assertEqual(
            prep.snap_back(date(2026, 9, 15), self.days), date(2026, 9, 15))

    def test_saturday_snaps_back_to_friday(self):
        self.assertEqual(
            prep.snap_back(date(2026, 9, 19), self.days), date(2026, 9, 18))

    def test_date_before_the_first_day_returns_none(self):
        self.assertIsNone(prep.snap_back(date(2026, 8, 4), self.days))


class TestDeriveCalendarBasis(unittest.TestCase):
    def test_order_counts_calendar_days_then_snaps(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = lab_block("INV-4", date(2026, 9, 15), {"order": 21})
        actions = prep.derive(blocks, days)

        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action.action, "order")
        self.assertEqual(action.basis, "calendar")
        self.assertEqual(action.raw_date, date(2026, 8, 25))
        self.assertEqual(action.date, date(2026, 8, 25))
        self.assertEqual(action.snapped_days, 0)

    def test_calendar_date_landing_on_a_weekend_snaps_backward(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        # Lab day Tue Sep 15 2026. A 2-day calendar lead lands on Sun Sep 13,
        # which must snap back to Fri Sep 11 — two days earlier, never later.
        blocks = lab_block("INV-4", date(2026, 9, 15), {"arrive": 2})
        actions = prep.derive(blocks, days)
        self.assertEqual(actions[0].raw_date, date(2026, 9, 13))
        self.assertEqual(actions[0].date, date(2026, 9, 11))
        self.assertEqual(actions[0].snapped_days, 2)


class TestDeriveSchoolBasis(unittest.TestCase):
    def test_bench_counts_school_days_and_skips_the_weekend(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        # Tue Sep 15 minus 3 school days is Thu Sep 10.
        blocks = lab_block("INV-4", date(2026, 9, 15), {"bench": 3})
        actions = prep.derive(blocks, days)
        self.assertEqual(actions[0].basis, "school")
        self.assertEqual(actions[0].date, date(2026, 9, 10))
        self.assertEqual(actions[0].snapped_days, 0)


class TestDeriveOverBreaks(unittest.TestCase):
    def test_arrival_inside_a_recess_snaps_out_of_it(self):
        recess = {date(2026, 12, 21) + timedelta(days=n) for n in range(12)}
        days = instructional(date(2026, 8, 12), date(2027, 2, 28), skip=recess)
        # Lab Jan 26; arrive 21 calendar days earlier is Jan 5 — but make the
        # lead long enough to land inside the recess.
        blocks = lab_block("INV-8", date(2027, 1, 26), {"arrive": 33})
        actions = prep.derive(blocks, days)
        self.assertEqual(actions[0].raw_date, date(2026, 12, 24))
        self.assertEqual(actions[0].date, date(2026, 12, 18))
        self.assertEqual(actions[0].snapped_days, 6)


class TestDeriveShape(unittest.TestCase):
    def test_actions_come_back_in_chronological_order(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = lab_block(
            "INV-4", date(2026, 9, 15), {"order": 21, "arrive": 14, "bench": 2})
        actions = prep.derive(blocks, days)
        self.assertEqual([a.action for a in actions],
                         ["order", "arrive", "bench"])
        self.assertEqual(actions, sorted(actions, key=lambda a: a.date))

    def test_lab_without_a_prep_block_produces_nothing(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = [{"unit": 2, "entries": [{
            "id": "INV-4", "title": "T", "kind": "lab",
            "dates": [date(2026, 9, 15)]}]}]
        self.assertEqual(prep.derive(blocks, days), [])

    def test_non_lab_entries_are_ignored_even_with_a_prep_block(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = [{"unit": 2, "entries": [{
            "id": "2.7", "title": "Tonicity", "kind": "topic",
            "dates": [date(2026, 9, 15)], "prep": {"order": 21}}]}]
        self.assertEqual(prep.derive(blocks, days), [])

    def test_uses_the_labs_first_day_not_its_last(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = [{"unit": 2, "entries": [{
            "id": "INV-4", "title": "T", "kind": "lab",
            "dates": [date(2026, 9, 15), date(2026, 9, 16), date(2026, 9, 17)],
            "prep": {"bench": 1}}]}]
        actions = prep.derive(blocks, days)
        self.assertEqual(actions[0].lab_date, date(2026, 9, 15))
        self.assertEqual(actions[0].date, date(2026, 9, 14))

    def test_unknown_action_key_raises(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        blocks = lab_block("INV-4", date(2026, 9, 15), {"deliver": 3})
        with self.assertRaises(ValueError):
            prep.derive(blocks, days)


if __name__ == "__main__":
    unittest.main()
