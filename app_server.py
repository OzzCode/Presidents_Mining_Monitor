# python
import os
import logging

from waitress import serve
import main as app_main  # import module to access namespace (e.g., SCHEDULER)

# Optional: initialize DB and scheduler if your app depends on them
def _maybe_init_db():
    try:
        from core.db import init_db
        init_db()
    except Exception:
        # Safe to ignore if DB init is optional
        pass

def _maybe_start_scheduler():
    try:
        # Gate via env if you don’t want scheduler in all environments
        if os.getenv("ENABLE_SCHEDULER", "true").lower() == "true":
            from scheduler import start_scheduler
            scheduler = start_scheduler()
            # Expose the scheduler instance to main module so /readyz can report correctly
            try:
                app_main.SCHEDULER = scheduler
            except Exception:
                # Non-fatal: readyz will just report scheduler_ok=False
                pass
    except Exception as e:
        logging.getLogger(__name__).warning("Scheduler failed to start: %s", e)

def main():
    # Create the Flask app using the same factory as development entrypoint
    app = app_main.create_app()

    # One-time setup
    _maybe_init_db()
    _maybe_start_scheduler()

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    threads = int(os.getenv("WAITRESS_THREADS", "8"))  # adjust for your workload

    # Basic logging to stdout
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    # Serve with Waitress (production-grade WSGI server for Windows/Linux/macOS)
    serve(app, listen=f"{host}:{port}", threads=threads)

if __name__ == "__main__":
    main()
