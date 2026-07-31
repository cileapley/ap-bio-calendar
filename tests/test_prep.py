import dataclasses
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

    def test_same_date_actions_order_by_intent(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        # Tue Sep 15 lab. A 1-school-day bench lead and a 1-calendar-day
        # arrive lead both land on Mon Sep 14, so only the tie-break can
        # order them.
        #
        # The keys are deliberately written bench-then-arrive: derive()
        # iterates spec.items() in insertion order and list.sort() is stable,
        # so if the ACTION_ORDER tie-break were removed from the sort key the
        # actions would come back in insertion order — [bench, arrive] — and
        # this assertion would fail. Writing them arrive-first would let a
        # removed tie-break pass, because insertion order would already match
        # the expected output.
        blocks = lab_block("INV-4", date(2026, 9, 15),
                           {"bench": 1, "arrive": 1})
        actions = prep.derive(blocks, days)
        self.assertEqual([a.date for a in actions],
                         [date(2026, 9, 14), date(2026, 9, 14)])
        self.assertEqual([a.action for a in actions], ["arrive", "bench"])

    def test_school_lead_reaching_past_the_start_keeps_a_real_raw_date(self):
        days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        # Only 3 school days exist before Mon Aug 17, so a 10-day bench lead
        # overshoots the start of the year. The usable date clamps forward to
        # day one — but raw_date must stay genuinely out of range, because
        # that is what validate() keys its before-term warning on.
        blocks = lab_block("INV-4", date(2026, 8, 17), {"bench": 10})
        actions = prep.derive(blocks, days)
        self.assertEqual(actions[0].date, date(2026, 8, 12))
        self.assertLess(actions[0].raw_date, date(2026, 8, 12))
        # Not a backward snap: the clamp moved the date LATER, so the
        # backward-snap magnitude is zero and the renderers stay quiet.
        self.assertEqual(actions[0].snapped_days, 0)


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.days = instructional(date(2026, 8, 12), date(2027, 2, 28))
        self.first = date(2026, 8, 12)

    def _actions(self, spec, lab_date=date(2026, 9, 15), lab_id="INV-4"):
        return prep.derive(lab_block(lab_id, lab_date, spec), self.days)

    def test_clean_actions_produce_nothing(self):
        actions = self._actions({"order": 21, "arrive": 14, "bench": 2})
        warnings, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertEqual(warnings, [])
        self.assertEqual(errors, [])

    def test_date_in_the_past_warns(self):
        actions = self._actions({"order": 21})
        warnings, errors = prep.validate(actions, self.first, date(2026, 9, 1))
        self.assertEqual(errors, [])
        self.assertTrue(any("past" in w.lower() for w in warnings))

    def test_date_before_term_warns(self):
        # 42-day lead on a Sep 15 lab lands Aug 4, before the Aug 12 start.
        actions = self._actions({"order": 42})
        warnings, errors = prep.validate(actions, self.first, date(2026, 7, 1))
        self.assertEqual(errors, [])
        self.assertTrue(any("before" in w.lower() for w in warnings))

    def test_snapping_more_than_two_days_warns(self):
        recess = {date(2026, 12, 21) + timedelta(days=n) for n in range(12)}
        days = instructional(date(2026, 8, 12), date(2027, 2, 28), skip=recess)
        actions = prep.derive(
            lab_block("INV-8", date(2027, 1, 26), {"arrive": 33}), days)
        warnings, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertEqual(errors, [])
        self.assertTrue(any("break" in w.lower() for w in warnings))

    def test_snapping_two_days_or_less_does_not_warn(self):
        # A weekend snap of 1-2 days is routine, not worth a warning.
        actions = self._actions({"arrive": 2})
        warnings, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertEqual(errors, [])
        self.assertFalse(any("break" in w.lower() for w in warnings))

    def test_arrive_before_order_is_an_error(self):
        actions = self._actions({"order": 7, "arrive": 21})
        warnings, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertTrue(any("INV-4" in e for e in errors))

    def test_errors_name_the_lab(self):
        actions = self._actions({"order": 7, "arrive": 21}, lab_id="INV-9")
        _, errors = prep.validate(actions, self.first, date(2026, 8, 1))
        self.assertTrue(any("INV-9" in e for e in errors))


class TestRenderIcs(unittest.TestCase):
    def setUp(self):
        self.days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        self.course = {"title": "AP Biology", "school_year": "2026-27"}
        self.actions = prep.derive(
            lab_block("INV-4", date(2026, 9, 15),
                      {"order": 21, "arrive": 14, "bench": 2}),
            self.days)

    def _render(self):
        return prep.render_ics(
            self.actions, self.course, "20260731T120000Z", "apbio-2026-27")

    def test_uses_crlf_line_endings(self):
        text = self._render()
        self.assertIn("\r\n", text)
        # No bare LF: every newline must be preceded by a carriage return.
        for position, char in enumerate(text):
            if char == "\n":
                self.assertEqual(text[position - 1], "\r")

    def test_one_vevent_per_action(self):
        self.assertEqual(self._render().count("BEGIN:VEVENT"), 3)

    def test_summary_names_the_action_and_the_lab_date(self):
        text = self._render()
        self.assertIn("SUMMARY:Order: Investigation X — Test Lab", text)
        self.assertIn("lab Sep 15", text)

    def test_uids_are_stable_and_distinct(self):
        first = self._render()
        second = prep.render_ics(
            self.actions, self.course, "20260801T090000Z", "apbio-2026-27")
        uids = lambda t: sorted(
            l for l in t.split("\r\n") if l.startswith("UID:"))
        self.assertEqual(uids(first), uids(second))
        self.assertEqual(len(set(uids(first))), 3)

    def test_uid_is_independent_of_the_scheduled_date(self):
        # The invariant that matters: when a unit slips, a subscriber's
        # calendar must MOVE the existing event, not add a second one beside
        # the stale copy. That holds only if the UID derives from lab and
        # action and never from the date. Asserting the UID text merely
        # lacks a year is no good — the uid_domain legitimately contains one.
        later = prep.derive(
            lab_block("INV-4", date(2026, 10, 20),
                      {"order": 21, "arrive": 14, "bench": 2}),
            self.days)

        def uids(actions):
            text = prep.render_ics(
                actions, self.course, "20260731T120000Z", "apbio-2026-27")
            return sorted(
                line for line in text.split("\r\n") if line.startswith("UID:"))

        # Guard the premise: the two renders must genuinely differ in date,
        # or this test proves nothing.
        self.assertNotEqual([a.date for a in self.actions],
                            [a.date for a in later])
        self.assertEqual(uids(self.actions), uids(later))

    def test_all_day_events_end_the_following_day(self):
        text = self._render()
        self.assertIn("DTSTART;VALUE=DATE:20260825", text)
        self.assertIn("DTEND;VALUE=DATE:20260826", text)

    def test_calendar_name_marks_it_as_the_prep_feed(self):
        self.assertIn("X-WR-CALNAME:AP Biology 2026-27 Lab Prep",
                      self._render())

    def test_long_course_title_folds_every_header_line(self):
        # PRODID and X-WR-CALNAME interpolate the course title straight from
        # calendar.yaml. Nothing bounds its length, so the header must fold
        # exactly like the event blocks do.
        course = {"title": "AP Biology Honors — Periods 2, 3 and 5, Room 204",
                  "school_year": "2026-27"}
        text = prep.render_ics(
            self.actions, course, "20260731T120000Z", "apbio-2026-27")
        for line in text.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_long_lab_title_folds_event_lines(self):
        actions = prep.derive(
            lab_block("INV-9",
                      date(2026, 9, 15),
                      {"order": 21}),
            self.days)
        long_title = "Investigation 9 — " + "Restriction Enzyme Analysis " * 3
        actions = [dataclasses.replace(a, lab_title=long_title)
                   for a in actions]
        text = prep.render_ics(
            actions, self.course, "20260731T120000Z", "apbio-2026-27")
        for line in text.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)


class TestRenderHtml(unittest.TestCase):
    def setUp(self):
        self.days = instructional(date(2026, 8, 12), date(2026, 12, 18))
        self.course = {"title": "AP Biology", "school_year": "2026-27"}
        self.actions = prep.derive(
            lab_block("INV-4", date(2026, 9, 15),
                      {"order": 21, "arrive": 14, "bench": 2}),
            self.days)

    def _render(self, today=date(2026, 8, 1)):
        return prep.render_html(self.actions, self.course,
                                "2026-07-31 12:00", today)

    def test_declares_charset_and_viewport(self):
        html = self._render()
        self.assertIn('<meta charset="utf-8">', html)
        self.assertIn('name="viewport"', html)

    def test_makes_no_network_requests(self):
        import re as _re
        html = self._render()
        self.assertEqual(_re.findall(r'(?:src|href)\s*=', html), [])
        self.assertNotIn("@import", html)
        self.assertNotIn("url(", html)

    def test_lists_every_action(self):
        html = self._render()
        for label in ("Order", "Arrives", "Prep starts"):
            self.assertIn(label, html)

    def test_groups_by_month(self):
        self.assertIn("August 2026", self._render())

    def test_marks_past_actions(self):
        # today is after all three actions (Aug 25, Sep 1, Sep 11), so every
        # row carries the overdue class.
        #
        # Assert on the row markup, not a bare "overdue" substring: PREP_CSS
        # inlines a .row.overdue rule into every render, so a substring search
        # passes even when no row is marked.
        html = self._render(today=date(2026, 9, 20))
        self.assertEqual(html.count('class="row overdue"'), len(self.actions))

    def test_does_not_mark_future_actions(self):
        # today precedes every action, so no row is overdue and every row
        # carries the bare class.
        html = self._render(today=date(2026, 8, 1))
        self.assertNotIn('class="row overdue"', html)
        self.assertEqual(html.count('class="row"'), len(self.actions))

    def test_escapes_html_in_titles(self):
        actions = prep.derive(
            [{"unit": 2, "entries": [{
                "id": "INV-X", "title": "Lab <script>alert(1)</script>",
                "kind": "lab", "dates": [date(2026, 9, 15)],
                "prep": {"bench": 1}}]}],
            self.days)
        html = prep.render_html(actions, self.course, "s", date(2026, 8, 1))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_empty_action_list_still_renders_a_page(self):
        html = prep.render_html([], self.course, "s", date(2026, 8, 1))
        self.assertIn("<title>", html)


if __name__ == "__main__":
    unittest.main()
