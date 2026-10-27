from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from venice_pt.contracts.events import Event, EventKind, Phase
from venice_pt.store.db import get_db_connection, init_db


class EventLog:
    def __init__(self, db_path: Path | str | sqlite3.Connection) -> None:
        if isinstance(db_path, sqlite3.Connection):
            self.conn = db_path
        else:
            self.conn = get_db_connection(db_path)
        init_db(self.conn)

    def append(self, event: Event) -> Event:
        """Appends an event to the immutable log. Never updates or deletes."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO events (
                    id, engagement_id, ts, phase, actor, kind, tool, cmd,
                    payload, parent_id, tokens_in, tokens_out, cost_usd, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event.id,
                    event.engagement_id,
                    event.ts.isoformat(),
                    str(event.phase),
                    event.actor,
                    str(event.kind),
                    event.tool,
                    event.cmd,
                    json.dumps(event.payload),
                    event.parent_id,
                    event.tokens_in,
                    event.tokens_out,
                    event.cost_usd,
                    event.duration_ms,
                ),
            )
        return event

    def append_many(self, events: list[Event]) -> None:
        """Appends multiple events within a single transaction."""
        with self.conn:
            self.conn.executemany(
                """
                INSERT INTO events (
                    id, engagement_id, ts, phase, actor, kind, tool, cmd,
                    payload, parent_id, tokens_in, tokens_out, cost_usd, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        e.id,
                        e.engagement_id,
                        e.ts.isoformat(),
                        str(e.phase),
                        e.actor,
                        str(e.kind),
                        e.tool,
                        e.cmd,
                        json.dumps(e.payload),
                        e.parent_id,
                        e.tokens_in,
                        e.tokens_out,
                        e.cost_usd,
                        e.duration_ms,
                    )
                    for e in events
                ],
            )

    def get_event(self, event_id: str) -> Event | None:
        cur = self.conn.execute(
            """
            SELECT id, engagement_id, ts, phase, actor, kind, tool, cmd,
                   payload, parent_id, tokens_in, tokens_out, cost_usd, duration_ms
            FROM events WHERE id = ?;
            """,
            (event_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_event(row)

    def get_events(
        self, engagement_id: str, since_id: str | None = None
    ) -> list[Event]:
        query = """
            SELECT id, engagement_id, ts, phase, actor, kind, tool, cmd,
                   payload, parent_id, tokens_in, tokens_out, cost_usd, duration_ms
            FROM events WHERE engagement_id = ?
        """
        params: list[Any] = [engagement_id]
        if since_id:
            query += " AND rowid > (SELECT rowid FROM events WHERE id = ?)"
            params.append(since_id)
        query += " ORDER BY ts ASC, rowid ASC;"

        cur = self.conn.execute(query, params)
        return [self._row_to_event(row) for row in cur.fetchall()]

    def walk_chain(self, event_id: str) -> list[Event]:
        """Reconstructs the full provenance ancestry chain leading to event_id."""
        chain: list[Event] = []
        current_id: str | None = event_id
        while current_id:
            cur = self.conn.execute(
                """
                SELECT id, engagement_id, ts, phase, actor, kind, tool, cmd,
                       payload, parent_id, tokens_in, tokens_out, cost_usd, duration_ms
                FROM events WHERE id = ?;
                """,
                (current_id,),
            )
            row = cur.fetchone()
            if not row:
                break
            event = self._row_to_event(row)
            chain.append(event)
            current_id = event.parent_id
        chain.reverse()
        return chain

    @staticmethod
    def _row_to_event(row: tuple[Any, ...]) -> Event:
        return Event(
            id=row[0],
            engagement_id=row[1],
            ts=datetime.fromisoformat(row[2]),
            phase=Phase(row[3]),
            actor=row[4],
            kind=EventKind(row[5]),
            tool=row[6],
            cmd=row[7],
            payload=json.loads(row[8]),
            parent_id=row[9],
            tokens_in=row[10],
            tokens_out=row[11],
            cost_usd=row[12],
            duration_ms=row[13],
        )
