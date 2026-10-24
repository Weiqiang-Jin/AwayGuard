import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def local_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, time_utc TEXT NOT NULL,
            kind TEXT NOT NULL, details TEXT NOT NULL)""")
        self.db.commit()

    def add(self, kind, details, timestamp=None):
        with self.db:
            self.db.execute("INSERT INTO events(time_utc, kind, details) VALUES (?, ?, ?)",
                            (timestamp or utc_now(), kind, json.dumps(details, ensure_ascii=False)))

    def recent(self, limit=500):
        return self.db.execute("SELECT id, time_utc, kind, details FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def export(self, path):
        # Prevent spreadsheet formula execution in exported textual cells.
        def safe(value):
            value = str(value)
            return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["ID", "UTC时间", "本地时间", "事件", "详情"])
            for row in self.db.execute("SELECT id, time_utc, kind, details FROM events ORDER BY id"):
                writer.writerow([safe(row[0]), row[1], local_time(row[1]), safe(row[2]), safe(row[3])])

    def close(self):
        self.db.close()
