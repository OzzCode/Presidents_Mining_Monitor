"""Firmware management services.

This module provides helpers for managing firmware images and coordinating
firmware flashing jobs. The actual device-specific flashing implementation is
intentionally abstracted behind service methods so adapters can be added later
for each miner vendor/model.
"""

from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path
from typing import Iterable, Optional, List, Any
import logging

from sqlalchemy.orm import Session

from core.db import FirmwareImage, FirmwareFlashJob, SessionLocal
from config import FIRMWARE_UPLOAD_DIR, FIRMWARE_DEFAULT_CREDENTIALS, FIRMWARE_HTTP_VERIFY

# Replace the circular import:
# from scheduler import logger
logger = logging.getLogger(__name__)


class FirmwareService:
    """CRUD helpers for `FirmwareImage` records."""

    @staticmethod
    def create_image(
            session: Session,
            *,
            file_name: str,
            storage_path: str,
            checksum: str,
            size_bytes: int,
            vendor: Optional[str] = None,
            model: Optional[str] = None,
            version: Optional[str] = None,
            notes: Optional[str] = None,
            uploaded_by: Optional[str] = None,
    ) -> FirmwareImage:
        image = FirmwareImage(
            file_name=file_name,
            storage_path=storage_path,
            checksum=checksum,
            size_bytes=size_bytes,
            vendor=vendor,
            model=model,
            version=version,
            notes=notes,
            uploaded_by=uploaded_by,
        )
        session.add(image)
        session.commit()
        session.refresh(image)
        return image

    @staticmethod
    def list_images(session: Session) -> List[FirmwareImage]:
        return (
            session.query(FirmwareImage)
            .order_by(FirmwareImage.created_at.desc())
            .all()
        )

    @staticmethod
    def get_image(session: Session, image_id: int) -> Optional[FirmwareImage]:
        return session.query(FirmwareImage).filter(FirmwareImage.id == image_id).first()

    @staticmethod
    def resolve_image_path(image: FirmwareImage) -> Optional[Path]:
        if not image or not image.storage_path:
            return None

        path = Path(image.storage_path)
        if not path.is_absolute():
            path = (FIRMWARE_UPLOAD_DIR / path).resolve()
        else:
            path = path.resolve()

        upload_root = FIRMWARE_UPLOAD_DIR.resolve()
        try:
            path.relative_to(upload_root)
        except ValueError:
            return None

        if not path.exists() or not path.is_file():
            return None

        return path

    @staticmethod
    def deactivate_image(session: Session, image_id: int) -> bool:
        image = session.query(FirmwareImage).filter(FirmwareImage.id == image_id).first()
        if not image:
            return False
        image.is_active = False
        session.commit()
        return True


class FirmwareFlashService:
    """Orchestrates firmware flashing job lifecycle."""

    @staticmethod
    def create_job(
            session: Session,
            *,
            firmware_id: int,
            miner_ip: str,
            initiated_by: Optional[str] = None,
            metadata: Optional[dict] = None,
    ) -> FirmwareFlashJob:
        job = FirmwareFlashJob(
            job_id=str(uuid.uuid4()),
            firmware_id=firmware_id,
            miner_ip=miner_ip,
            initiated_by=initiated_by,
            extra_metadata=metadata or {},
            status="pending",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    @staticmethod
    def mark_started(session: Session, job: FirmwareFlashJob) -> FirmwareFlashJob:
        job.status = "in_progress"
        job.started_at = job.started_at or dt.datetime.utcnow()
        session.commit()
        return job

    @staticmethod
    def mark_progress(session: Session, job: FirmwareFlashJob, progress: int) -> FirmwareFlashJob:
        job.progress = max(0, min(progress, 100))
        job.status = job.status or "in_progress"
        job.updated_at = dt.datetime.utcnow()
        session.commit()
        return job

    @staticmethod
    def mark_completed(session: Session, job: FirmwareFlashJob) -> FirmwareFlashJob:
        job.status = "success"
        job.progress = 100
        job.completed_at = dt.datetime.utcnow()
        session.commit()
        return job

    @staticmethod
    def mark_failed(session: Session, job: FirmwareFlashJob, error_message: str) -> FirmwareFlashJob:
        job.status = "failed"
        job.error_message = error_message
        job.completed_at = dt.datetime.utcnow()
        session.commit()
        return job

    @staticmethod
    def get_job_by_public_id(session: Session, job_id: str) -> Optional[FirmwareFlashJob]:
        return (
            session.query(FirmwareFlashJob)
            .filter(FirmwareFlashJob.job_id == job_id)
            .first()
        )

    @staticmethod
    def list_jobs(session: Session, *, miner_ip: Optional[str] = None) -> list[type[FirmwareFlashJob]]:
        query = session.query(FirmwareFlashJob).order_by(FirmwareFlashJob.created_at.desc())
        if miner_ip:
            query = query.filter(FirmwareFlashJob.miner_ip == miner_ip)
        return query.limit(100).all()

    @staticmethod
    def list_active_jobs(session: Session) -> list[type[FirmwareFlashJob]]:
        return (
            session.query(FirmwareFlashJob)
            .filter(FirmwareFlashJob.status.in_(["pending", "in_progress"]))
            .order_by(FirmwareFlashJob.created_at.asc())
            .limit(20)
            .all()
        )

    @staticmethod
    def process_jobs(session: Session, *, batch_size: int = 10) -> dict:
        """Process pending firmware flash jobs.
        
        This method processes a batch of pending firmware flash jobs, handling the actual
        flashing process for each supported miner type.
        
        Args:
            session: Database session
            batch_size: Maximum number of jobs to process in this batch
            
        Returns:
            Dictionary with job processing statistics
        """
        from core.firmware_flasher import get_flasher_for_miner, FlashError, UnsupportedVendorError, BaseFlasher
        from core.miner import MinerClient

        jobs = FirmwareFlashService.list_active_jobs(session)[:batch_size]
        summary = {
            "checked": len(jobs),
            "started": 0,
            "progressed": 0,
            "completed": 0,
            "failed": 0,
        }

        for job in jobs:
            try:
                extra = job.extra_metadata or {}
                history = extra.get("history", [])
                firmware = FirmwareService.get_image(session, job.firmware_id)

                if not firmware:
                    raise ValueError(f"Firmware image {job.firmware_id} not found")

                firmware_path = FirmwareService.resolve_image_path(firmware)
                if not firmware_path:
                    raise ValueError(f"Firmware file not found at {firmware.storage_path}")

                if job.status == "pending":
                    # Guard: avoid starting a second job for the same miner concurrently
                    existing_active = (
                        session.query(FirmwareFlashJob)
                        .filter(
                            FirmwareFlashJob.miner_ip == job.miner_ip,
                            FirmwareFlashJob.status == 'in_progress',
                            FirmwareFlashJob.id != job.id,
                        )
                        .first()
                    )
                    if existing_active:
                        # leave as pending; next scheduler tick will try again
                        continue

                    # Start the flashing process
                    FirmwareFlashService.mark_started(session, job)

                    # Initialize miner client to get model info
                    try:
                        miner_client = MinerClient(job.miner_ip)
                        summary_data = miner_client.get_summary()
                        miner_model = summary_data.get('Type', 'Unknown')

                        # Store miner info for reference
                        extra['miner_info'] = {
                            'model': miner_model,
                            'ip': job.miner_ip,
                            'original_firmware': summary_data.get('Firmware', 'Unknown'),
                        }
                    except Exception as e:
                        logger.warning(f"Could not get miner info for {job.miner_ip}: {str(e)}")
                        miner_model = 'Unknown'

                    # Log start of flashing
                    history.append({
                        "timestamp": dt.datetime.utcnow().isoformat(),
                        "message": f"Starting firmware update to {firmware.file_name}",
                        "miner_model": miner_model,
                    })
                    job.extra_metadata = {**extra, "history": history}
                    session.commit()
                    summary["started"] += 1

                    # Determine vendor for credential fallback (prefer firmware metadata)
                    vendor = (firmware.vendor or '').strip().lower()
                    model_lower = (miner_model or '').lower()
                    if not vendor:
                        if 'antminer' in model_lower or 'bitmain' in model_lower:
                            vendor = 'bitmain'
                        elif 'whatsminer' in model_lower or 'microbt' in model_lower:
                            vendor = 'microbt'
                        elif 'avalon' in model_lower or 'canaan' in model_lower:
                            vendor = 'canaan'
                        elif 'innosilicon' in model_lower:
                            vendor = 'innosilicon'

                    creds_cfg = FIRMWARE_DEFAULT_CREDENTIALS.get(vendor, {})
                    auth = BaseFlasher.build_auth(
                        creds_cfg.get('auth'), creds_cfg.get('user'), creds_cfg.get('password')
                    )
                    verify = FIRMWARE_HTTP_VERIFY

                    # Begin the actual flashing process
                    try:
                        # Route by vendor if known, else fall back to miner-reported model
                        route_key = vendor or miner_model
                        flasher = get_flasher_for_miner(route_key or 'unknown', job.miner_ip)
                        # Inject runtime parameters
                        flasher.auth = auth
                        try:
                            # verify may be bool or CA bundle path; config gives bool now
                            flasher.session.verify = verify
                        except Exception:
                            pass

                        # Use a thread-local throttle to reduce DB commits
                        last_state = {'progress': -1, 'ts': 0.0}
                        job_id = job.job_id

                        def progress_callback(progress: int, message: str):
                            """Update job progress and log message."""
                            import time as _t
                            now = _t.time()
                            if progress < 100 and (progress - last_state['progress'] < 5) and (
                                    now - last_state['ts'] < 1.0):
                                return
                            session2 = SessionLocal()
                            try:
                                j = FirmwareFlashService.get_job_by_public_id(session2, job_id)
                                if not j:
                                    return
                                # Update progress and history
                                FirmwareFlashService.mark_progress(session2, j, progress)
                                h = (j.extra_metadata or {}).get("history", [])
                                h.append({
                                    "timestamp": dt.datetime.utcnow().isoformat(),
                                    "message": message,
                                    "progress": progress
                                })
                                j.extra_metadata = {**(j.extra_metadata or {}), "history": h}
                                session2.commit()
                                last_state['progress'] = progress
                                last_state['ts'] = now
                            finally:
                                session2.close()

                        # Start flashing in a separate thread to avoid blocking
                        import threading

                        def flash_worker():
                            """Worker function to run the flashing process."""
                            # Use a fresh session inside the worker thread
                            session2 = SessionLocal()
                            try:
                                j = FirmwareFlashService.get_job_by_public_id(session2, job_id)
                                if not j:
                                    return
                                # Resolve firmware and path again inside thread
                                f = FirmwareService.get_image(session2, j.firmware_id)
                                p = FirmwareService.resolve_image_path(f)
                                success, message = flasher.flash(p, progress_callback)

                                if success:
                                    FirmwareFlashService.mark_completed(session2, j)
                                    progress_callback(100, f"Firmware update completed successfully: {message}")
                                    logger.info(
                                        f"Firmware update for {j.miner_ip} completed successfully (job_id={j.job_id})")
                                else:
                                    raise FlashError(message)

                            except Exception as e:
                                error_msg = f"Firmware update failed: {str(e)}"
                                logger.error(f"Error flashing {job.miner_ip}: {error_msg}", exc_info=True)
                                # Mark failed with a new session to avoid cross-thread session issues
                                session3 = SessionLocal()
                                try:
                                    j2 = FirmwareFlashService.get_job_by_public_id(session3, job_id)
                                    if j2:
                                        FirmwareFlashService.mark_failed(session3, j2, error_msg)
                                        # Append to history
                                        h2 = (j2.extra_metadata or {}).get("history", [])
                                        h2.append({
                                            "timestamp": dt.datetime.utcnow().isoformat(),
                                            "message": error_msg,
                                            "error": True
                                        })
                                        j2.extra_metadata = {**(j2.extra_metadata or {}), "history": h2}
                                        session3.commit()
                                finally:
                                    session3.close()
                            finally:
                                session2.close()

                        # Start the flashing process in a separate thread
                        thread = threading.Thread(target=flash_worker, daemon=True)
                        thread.start()

                        # Mark as in progress and update summary
                        job.status = "in_progress"
                        session.commit()

                    except UnsupportedVendorError as e:
                        raise FlashError(f"Unsupported miner model: {miner_model}") from e
                    except Exception as e:
                        raise FlashError(f"Failed to initialize flasher: {str(e)}") from e

                # For in-progress jobs, just update the status
                elif job.status == "in_progress":
                    # Job is being processed by the worker thread, just update the timestamp
                    job.updated_at = dt.datetime.utcnow()
                    session.commit()
                    summary["progressed"] += 1

            except Exception as exc:
                logger.error(f"Error processing firmware job {job.id}: {str(exc)}", exc_info=True)
                FirmwareFlashService.mark_failed(session, job, str(exc))
                summary["failed"] += 1

        return summary

    @staticmethod
    def flash_firmware_placeholder(job: FirmwareFlashJob) -> None:
        """Placeholder hook for actual flashing logic.

        This method is intentionally left as a stub. When implementing real
        firmware flashing, hook the vendor-specific logic here and ensure the
        job record is updated via the other helper methods.
        """
        raise NotImplementedError("Firmware flashing logic not implemented yet")
