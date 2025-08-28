import logging
import sys
import sqlite3
from sqlalchemy.exc import DatabaseError as SADataBaseError
from core.db import SessionLocal, ErrorEvent


class DBHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._disabled_due_to_db_error = False

    def emit(self, record: logging.LogRecord):
        # If we previously detected a fatal DB error, skip to prevent cascades.
        if self._disabled_due_to_db_error:
            return

        session = None
        try:
            session = SessionLocal()
            context = {}
            for k in ("job_id", "path", "endpoint"):
                if hasattr(record, k):
                    context[k] = getattr(record, k)
            ev = ErrorEvent(
                level=record.levelname,
                component=getattr(record, "component", "app"),
                miner_ip=getattr(record, "miner_ip", None),
                message=record.getMessage(),
                context=context,
                traceback=record.exc_text or None,
            )
            session.add(ev)
            session.commit()
        except (sqlite3.DatabaseError, SADataBaseError) as e:
            # Rollback and disable the handler if the DB is corrupted.
            if session is not None:
                try:
                    session.rollback()
                except Exception:
                    pass
            msg = str(e).lower()
            if "malformed" in msg or "database disk image is malformed" in msg:
                self._disabled_due_to_db_error = True
                print(
                    "[DBHandler] Disabled DB logging due to SQLite corruption: 'database disk image is malformed'. "
                    "Please recover or replace the database.",
                    file=sys.stderr,
                )
            else:
                # For other DB errors, print a concise diagnostic but don't disable permanently.
                print(f"[DBHandler] Database error during log persist: {e}", file=sys.stderr)
        except Exception as e:
            # Rollback on unexpected errors and print a message (avoid logging to prevent recursion).
            if session is not None:
                try:
                    session.rollback()
                except Exception:
                    pass
            print(f"[DBHandler] Unexpected error during log persist: {e}", file=sys.stderr)
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
