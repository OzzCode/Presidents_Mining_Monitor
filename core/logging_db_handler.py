import logging
from core.db import SessionLocal, ErrorEvent


class DBHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
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
            session.add(ev);
            session.commit()
        except Exception:
            pass
        finally:
            try:
                session.close()
            except Exception:
                pass
