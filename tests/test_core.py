import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from awayguard.events import EventReader, parse_events, public_event
from awayguard.monitor import ActivityTracker, IdleVisibility
from awayguard.storage import Store


def event(record=10, event_id=4801, data=None):
    return {"event_id": event_id, "record_id": record, "time": "2026-10-24T00:00:00.0000000Z", "data": data or {}}


class IdleVisibilityTests(unittest.TestCase):
    def test_idle_hides_at_ten_seconds_and_can_repeat(self):
        timer = IdleVisibility()
        self.assertFalse(timer.should_hide(100, 1))
        timer.show(100, 1)
        self.assertFalse(timer.should_hide(109.99, 1))
        self.assertTrue(timer.should_hide(110, 1))
        timer.clear()
        self.assertFalse(timer.should_hide(120, 1))
        timer.show(125, 2)
        self.assertTrue(timer.should_hide(135, 2))

    def test_input_resets_idle_even_at_deadline(self):
        timer = IdleVisibility()
        timer.show(0, 100)
        self.assertFalse(timer.should_hide(10, 101))
        self.assertFalse(timer.should_hide(19.9, 101))
        self.assertTrue(timer.should_hide(20, 101))

    def test_stop_cancels_idle_and_tick_wrap_is_activity(self):
        timer = IdleVisibility()
        timer.show(0, 0xFFFFFFFF)
        self.assertFalse(timer.should_hide(10, 0))
        timer.clear()
        self.assertFalse(timer.should_hide(100, 0))


class ActivityTests(unittest.TestCase):
    def test_every_new_activity_warns_without_cooldown(self):
        tracker = ActivityTracker(100)
        self.assertEqual(tracker.update(0, 100, None), ([], False))
        self.assertTrue(tracker.update(1, 101, None)[1])
        self.assertTrue(tracker.update(2, 102, None)[1])
        self.assertFalse(tracker.update(3, 102, None)[1])
        self.assertTrue(tracker.update(62, 103, None)[1])

    def test_app_switch_only_near_input(self):
        tracker = ActivityTracker(100)
        window = {"pid": 1, "window": 10, "process": "example.exe"}
        self.assertEqual(tracker.update(0, 100, window)[0], [])
        self.assertEqual(len(tracker.update(1, 101, window)[0]), 2)
        self.assertEqual(tracker.update(2, 101, window)[0], [])
        other = dict(window, window=20)
        self.assertEqual(tracker.update(20, 101, other)[0], [])
        self.assertEqual(len(tracker.update(21, 102, other)[0]), 2)

    def test_tick_wraparound(self):
        tracker = ActivityTracker(0xFFFFFFFF)
        self.assertTrue(tracker.update(1, 0, None)[1])


class AuditTests(unittest.TestCase):
    def test_parse_namespaced_xml(self):
        xml = '''<Events><Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><System><EventID>4801</EventID><EventRecordID>42</EventRecordID><TimeCreated SystemTime="2026-10-24T00:00:00Z"/></System><EventData><Data Name="TargetUserName">Alice &amp; Bob</Data><Data Name="SessionId">1</Data></EventData></Event></Events>'''
        result = parse_events(xml)[0]
        self.assertEqual(result["record_id"], 42)
        self.assertEqual(public_event(result)[1]["TargetUserName"], "Alice & Bob")

    def test_filter_network_and_service_logons(self):
        for kind in ("3", "4", "5"):
            self.assertIsNone(public_event(event(event_id=4624, data={"LogonType": kind})))
        self.assertIsNotNone(public_event(event(event_id=4625, data={"LogonType": "7"})))

    @patch("awayguard.events.query")
    def test_baseline_does_not_import_old_events(self, query):
        query.return_value = [event(10)]
        reader = EventReader()
        self.assertEqual(reader.poll()[0], [])
        self.assertEqual(reader.cursor, 10)
        query.side_effect = [[event(13)], [event(11), event(13)]]
        self.assertEqual(len(reader.poll()[0]), 2)
        self.assertEqual(reader.cursor, 13)
        query.side_effect = [[event(13)], []]
        self.assertEqual(reader.poll()[0], [])

    @patch("awayguard.events.query")
    def test_full_page_does_not_skip_backlog(self, query):
        reader = EventReader()
        reader.cursor = 10
        query.side_effect = [[event(999)], [event(i) for i in range(11, 211)]]
        self.assertEqual(len(reader.poll()[0]), 200)
        self.assertEqual(reader.cursor, 210)

    @patch("awayguard.events.query")
    def test_log_reset(self, query):
        reader = EventReader()
        reader.cursor = 999
        query.side_effect = [[event(2)], [event(1, 1102), event(2)]]
        items, status = reader.poll()
        self.assertEqual(len(items), 2)
        self.assertIn("重置", status)
        self.assertEqual(reader.cursor, 2)

    @patch("awayguard.events.query", side_effect=RuntimeError("access denied"))
    def test_failed_query_preserves_cursor(self, query):
        reader = EventReader()
        reader.cursor = 10
        with self.assertRaises(RuntimeError):
            reader.poll()
        self.assertEqual(reader.cursor, 10)


class StorageTests(unittest.TestCase):
    def test_persistence_and_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "events.sqlite3"
            store = Store(database)
            store.add("=formula", {"应用": "记事本"}, "2026-10-24T00:00:00Z")
            store.close()
            store = Store(database)
            self.assertEqual(len(store.recent()), 1)
            target = Path(folder) / "export.csv"
            store.export(target)
            with target.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[1][3], "'=formula")
            self.assertIn("记事本", rows[1][4])
            store.close()


if __name__ == "__main__":
    unittest.main()
