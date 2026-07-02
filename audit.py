from __future__ import annotations

import atexit
import json
import queue
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from db_credentials import get_sql_connection


@dataclass(frozen=True)
class _AuditEvent:
    category: str
    action: str
    outcome: str
    user_id: Optional[int]
    username: Optional[str]
    details: Optional[str]


_events: queue.Queue[_AuditEvent] = queue.Queue(maxsize=5000)
_stop = threading.Event()
_worker: Optional[threading.Thread] = None
_lock = threading.Lock()
_current_user_id: Optional[int] = None
_current_username: Optional[str] = None
_machine_name = socket.gethostname()[:128]


def initialize_schema() -> None:
    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        IF OBJECT_ID(N'dbo.application_audit_log', N'U') IS NULL
        BEGIN
            CREATE TABLE dbo.application_audit_log (
                id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_application_audit_log PRIMARY KEY,
                occurred_at DATETIME2(3) NOT NULL CONSTRAINT DF_application_audit_log_occurred_at DEFAULT SYSUTCDATETIME(),
                category VARCHAR(24) NOT NULL,
                action VARCHAR(64) NOT NULL,
                outcome VARCHAR(16) NOT NULL,
                user_id INT NULL,
                username NVARCHAR(80) NULL,
                machine_name NVARCHAR(128) NULL,
                details NVARCHAR(2000) NULL
            );
            CREATE INDEX IX_application_audit_log_category_time
                ON dbo.application_audit_log(category, occurred_at DESC);
            CREATE INDEX IX_application_audit_log_user_time
                ON dbo.application_audit_log(user_id, occurred_at DESC) WHERE user_id IS NOT NULL;
        END
        """)
        conn.commit()
    finally:
        conn.close()


def set_user(user_id: Optional[int], username: Optional[str]) -> None:
    global _current_user_id, _current_username
    with _lock:
        _current_user_id = user_id
        _current_username = username


def log(category: str, action: str, *, outcome: str = "success",
        details: Optional[dict[str, Any]] = None,
        user_id: Optional[int] = None, username: Optional[str] = None) -> None:
    _ensure_worker()
    with _lock:
        event_user_id = _current_user_id if user_id is None else user_id
        event_username = _current_username if username is None else username
    encoded = json.dumps(details, ensure_ascii=True, separators=(",", ":"))[:2000] if details else None
    event = _AuditEvent(category[:24], action[:64], outcome[:16], event_user_id,
                        (event_username or "")[:80] or None, encoded)
    try:
        _events.put_nowait(event)
    except queue.Full:
        pass  # Auditing must never block scanning or the UI.


def shutdown(timeout: float = 2.0) -> None:
    _stop.set()
    worker = _worker
    if worker and worker.is_alive():
        worker.join(timeout)


def export_to_excel(path: str) -> int:
    from openpyxl import Workbook

    conn = get_sql_connection()
    row_count = 0
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT occurred_at, category, action, outcome, user_id,
                   username, machine_name, details
            FROM dbo.application_audit_log
            ORDER BY occurred_at DESC, id DESC
        """)
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("Audit Logs")
        sheet.append([
            "Occurred At (UTC)", "Category", "Action", "Outcome", "User ID",
            "Username", "Machine", "Details",
        ])
        while True:
            rows = cursor.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                sheet.append(list(row))
                row_count += 1
        workbook.save(path)
        return row_count
    finally:
        conn.close()


def _ensure_worker() -> None:
    global _worker
    with _lock:
        if _worker and _worker.is_alive():
            return
        _stop.clear()
        _worker = threading.Thread(target=_run, name="audit-writer", daemon=True)
        _worker.start()


def _run() -> None:
    while not _stop.is_set() or not _events.empty():
        batch: list[_AuditEvent] = []
        try:
            batch.append(_events.get(timeout=0.5))
        except queue.Empty:
            continue
        while len(batch) < 100:
            try:
                batch.append(_events.get_nowait())
            except queue.Empty:
                break
        try:
            _write_batch(batch)
        except Exception:
            time.sleep(0.5)
        finally:
            for _ in batch:
                _events.task_done()


def _write_batch(batch: list[_AuditEvent]) -> None:
    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.fast_executemany = True
        cursor.executemany(
            """INSERT INTO dbo.application_audit_log
               (category, action, outcome, user_id, username, machine_name, details)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(e.category, e.action, e.outcome, e.user_id, e.username, _machine_name, e.details)
             for e in batch],
        )
        conn.commit()
    finally:
        conn.close()


atexit.register(shutdown)
