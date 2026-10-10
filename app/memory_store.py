"""SQLite event log and deterministic materialized object state."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.schemas import EventRecord, ObjectRecord, ObjectState, VLMEventResult, ZoneRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    reference_image_path TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS zones (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    polygon_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    object_id TEXT,
    from_zone_id TEXT,
    to_zone_id TEXT,
    confidence REAL NOT NULL,
    accepted INTEGER NOT NULL DEFAULT 0,
    user_corrected INTEGER NOT NULL DEFAULT 0,
    visible_evidence_json TEXT NOT NULL DEFAULT '[]',
    uncertainty_reason TEXT,
    pre_image_path TEXT,
    post_image_path TEXT,
    composite_path TEXT,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model_latency_ms INTEGER,
    raw_response_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(object_id) REFERENCES objects(id),
    FOREIGN KEY(from_zone_id) REFERENCES zones(id),
    FOREIGN KEY(to_zone_id) REFERENCES zones(id)
);
CREATE TABLE IF NOT EXISTS object_state (
    object_id TEXT PRIMARY KEY,
    zone_id TEXT,
    last_event_id INTEGER,
    confidence REAL NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(object_id) REFERENCES objects(id),
    FOREIGN KEY(zone_id) REFERENCES zones(id),
    FOREIGN KEY(last_event_id) REFERENCES events(id)
);
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    referenced_event_ids_json TEXT NOT NULL DEFAULT '[]',
    latency_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    labels_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ended_at ON events(ended_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_events_object ON events(object_id, ended_at DESC, id DESC);
"""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MemoryStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)
            db.execute(
                """INSERT OR IGNORE INTO zones(id, display_name, polygon_json, active, created_at)
                   VALUES('outside_view', 'Outside view', '[[0,0],[0,1],[1,1]]', 0, ?)""",
                (now_iso(),),
            )

    def add_object(self, record: ObjectRecord) -> ObjectRecord:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                """INSERT INTO objects(id, display_name, aliases_json, reference_image_path, active, created_at)
                   VALUES(?, ?, ?, ?, ?, ?)""",
                (
                    record.id,
                    record.display_name,
                    json.dumps(record.aliases),
                    record.reference_image_path,
                    int(record.active),
                    now_iso(),
                ),
            )
            db.commit()
        return record

    def list_objects(self, active_only: bool = True) -> list[ObjectRecord]:
        query = "SELECT * FROM objects" + (" WHERE active=1" if active_only else "") + " ORDER BY id"
        with self.connect() as db:
            rows = db.execute(query).fetchall()
        return [
            ObjectRecord(
                id=row["id"],
                display_name=row["display_name"],
                aliases=json.loads(row["aliases_json"]),
                reference_image_path=row["reference_image_path"],
                active=bool(row["active"]),
            )
            for row in rows
        ]

    def delete_object(self, object_id: str) -> str | None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT reference_image_path FROM objects WHERE id=?", (object_id,)).fetchone()
            if row is None:
                db.rollback()
                raise KeyError(f"object {object_id} not found")
            db.execute("UPDATE objects SET active=0 WHERE id=?", (object_id,))
            db.execute("DELETE FROM object_state WHERE object_id=?", (object_id,))
            db.commit()
        return row["reference_image_path"]

    def add_zone(self, record: ZoneRecord) -> ZoneRecord:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO zones(id, display_name, polygon_json, active, created_at) VALUES(?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.display_name,
                    json.dumps(record.polygon),
                    int(record.active),
                    now_iso(),
                ),
            )
            db.commit()
        return record

    def list_zones(self, active_only: bool = True) -> list[ZoneRecord]:
        query = "SELECT * FROM zones" + (" WHERE active=1" if active_only else "") + " ORDER BY id"
        with self.connect() as db:
            rows = db.execute(query).fetchall()
        return [
            ZoneRecord(
                id=row["id"],
                display_name=row["display_name"],
                polygon=json.loads(row["polygon_json"]),
                active=bool(row["active"]),
            )
            for row in rows
        ]

    def delete_zone(self, zone_id: str) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE zones SET active=0 WHERE id=?", (zone_id,))
            db.commit()

    def add_event(
        self,
        result: VLMEventResult,
        *,
        accepted: bool,
        model_name: str,
        model_latency_ms: int | None,
        raw_response_json: dict,
        pre_image_path: str | None,
        post_image_path: str | None,
        composite_path: str | None,
        prompt_version: str = "event-v1",
    ) -> EventRecord:
        timestamp = now_iso()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                """INSERT INTO events(
                    started_at, ended_at, event_type, object_id, from_zone_id, to_zone_id,
                    confidence, accepted, visible_evidence_json, uncertainty_reason,
                    pre_image_path, post_image_path, composite_path, model_name,
                    prompt_version, model_latency_ms, raw_response_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    timestamp,
                    timestamp,
                    result.event_type,
                    result.object_id,
                    result.from_zone_id,
                    result.to_zone_id,
                    result.confidence,
                    int(accepted),
                    json.dumps(result.visible_evidence),
                    result.uncertainty_reason,
                    pre_image_path,
                    post_image_path,
                    composite_path,
                    model_name,
                    prompt_version,
                    model_latency_ms,
                    json.dumps(raw_response_json),
                    timestamp,
                ),
            )
            event_id = int(cursor.lastrowid)
            if accepted and result.object_id and result.event_type in {"move", "appear", "disappear"}:
                if result.event_type in {"move", "appear"}:
                    current_zone = result.to_zone_id
                elif result.event_type == "disappear":
                    current_zone = "outside_view"
                db.execute(
                    """INSERT INTO object_state(object_id, zone_id, last_event_id, confidence, updated_at)
                       VALUES(?, ?, ?, ?, ?)
                       ON CONFLICT(object_id) DO UPDATE SET zone_id=excluded.zone_id,
                       last_event_id=excluded.last_event_id, confidence=excluded.confidence,
                       updated_at=excluded.updated_at""",
                    (result.object_id, current_zone, event_id, result.confidence, timestamp),
                )
            db.commit()
        return self.get_event(event_id)

    def get_event(self, event_id: int) -> EventRecord:
        with self.connect() as db:
            row = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if row is None:
            raise KeyError(f"event {event_id} not found")
        return self._event(row)

    def list_events(self, limit: int = 50) -> list[EventRecord]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._event(row) for row in rows]

    @staticmethod
    def _event(row: sqlite3.Row) -> EventRecord:
        return EventRecord(
            id=row["id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            event_type=row["event_type"],
            object_id=row["object_id"],
            from_zone_id=row["from_zone_id"],
            to_zone_id=row["to_zone_id"],
            confidence=row["confidence"],
            accepted=bool(row["accepted"]),
            user_corrected=bool(row["user_corrected"]),
            visible_evidence=json.loads(row["visible_evidence_json"]),
            uncertainty_reason=row["uncertainty_reason"],
            pre_image_path=row["pre_image_path"],
            post_image_path=row["post_image_path"],
            composite_path=row["composite_path"],
            model_name=row["model_name"],
            prompt_version=row["prompt_version"],
            model_latency_ms=row["model_latency_ms"],
            raw_response_json=json.loads(row["raw_response_json"]),
        )

    def get_object_state(self, object_id: str) -> ObjectState | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM object_state WHERE object_id=?", (object_id,)).fetchone()
        if row is None:
            return None
        return ObjectState(
            object_id=row["object_id"],
            zone_id=row["zone_id"],
            last_event_id=row["last_event_id"],
            confidence=row["confidence"],
            updated_at=row["updated_at"],
        )

    def get_state_rows(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                """SELECT o.id object_id, o.display_name, o.aliases_json, s.zone_id,
                          z.display_name zone_name, s.last_event_id, s.confidence, s.updated_at
                   FROM objects o LEFT JOIN object_state s ON s.object_id=o.id
                   LEFT JOIN zones z ON z.id=s.zone_id WHERE o.active=1 ORDER BY o.id"""
            ).fetchall()
        return [dict(row) for row in rows]

    def rebuild_state(self) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM object_state")
            events = db.execute(
                "SELECT * FROM events WHERE accepted=1 ORDER BY ended_at ASC, id ASC"
            ).fetchall()
            state: dict[str, tuple[str, int, float, str]] = {}
            for event in events:
                object_id = event["object_id"]
                if not object_id:
                    continue
                event_type = event["event_type"]
                if event_type in {"move", "appear"}:
                    zone_id = event["to_zone_id"]
                elif event_type == "disappear":
                    zone_id = "outside_view"
                else:
                    continue
                state[object_id] = (zone_id, event["id"], event["confidence"], event["ended_at"])
            for object_id, (zone_id, event_id, confidence, updated_at) in state.items():
                db.execute(
                    "INSERT INTO object_state(object_id, zone_id, last_event_id, confidence, updated_at) VALUES(?, ?, ?, ?, ?)",
                    (object_id, zone_id, event_id, confidence, updated_at),
                )
            db.commit()

    def set_event_decision(self, event_id: int, accepted: bool) -> EventRecord:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute("UPDATE events SET accepted=? WHERE id=?", (int(accepted), event_id))
            if cursor.rowcount == 0:
                db.rollback()
                raise KeyError(f"event {event_id} not found")
            db.commit()
        self.rebuild_state()
        return self.get_event(event_id)

    def correct_event(
        self,
        event_id: int,
        *,
        event_type: str,
        object_id: str | None,
        from_zone_id: str | None,
        to_zone_id: str | None,
    ) -> EventRecord:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                """UPDATE events SET event_type=?, object_id=?, from_zone_id=?, to_zone_id=?,
                   accepted=1, user_corrected=1 WHERE id=?""",
                (event_type, object_id, from_zone_id, to_zone_id, event_id),
            )
            if cursor.rowcount == 0:
                db.rollback()
                raise KeyError(f"event {event_id} not found")
            db.commit()
        self.rebuild_state()
        return self.get_event(event_id)

    def insert_query(self, question: str, answer: str, event_ids: list[int], latency_ms: int) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO queries(question, answer, referenced_event_ids_json, latency_ms, created_at) VALUES(?, ?, ?, ?, ?)",
                (question, answer, json.dumps(event_ids), latency_ms, now_iso()),
            )
            db.commit()

    def count_events(self) -> int:
        with self.connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def count_evidence(self) -> int:
        with self.connect() as db:
            row = db.execute(
                "SELECT COUNT(*) FROM events WHERE pre_image_path IS NOT NULL OR post_image_path IS NOT NULL"
            ).fetchone()
        return int(row[0])

    def delete_all_memory(self) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for table in ("object_state", "events", "queries", "metrics", "objects", "zones", "settings"):
                db.execute(f"DELETE FROM {table}")
            db.commit()

    def integrity_check(self) -> str:
        with self.connect() as db:
            return str(db.execute("PRAGMA integrity_check").fetchone()[0])

