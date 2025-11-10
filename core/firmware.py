"""Firmware management services.

This module provides helpers for managing firmware images and coordinating
firmware flashing jobs. The actual device-specific flashing implementation is
intentionally abstracted behind service methods so adapters can be added later
for each miner vendor/model.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Iterable, Optional, List, Any

from sqlalchemy.orm import Session

from core.db import FirmwareImage, FirmwareFlashJob


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

                if job.status == "pending":
                    FirmwareFlashService.mark_started(session, job)
                    FirmwareFlashService.mark_progress(session, job, max(job.progress or 0, 10))
                    history.append({
                        "timestamp": dt.datetime.utcnow().isoformat(),
                        "message": "Job started (simulation)",
                    })
                    summary["started"] += 1
                else:
                    new_progress = min(100, (job.progress or 0) + 35)
                    if new_progress >= 100:
                        FirmwareFlashService.mark_completed(session, job)
                        history.append({
                            "timestamp": dt.datetime.utcnow().isoformat(),
                            "message": "Job completed successfully (simulation)",
                        })
                        summary["completed"] += 1
                    else:
                        FirmwareFlashService.mark_progress(session, job, new_progress)
                        history.append({
                            "timestamp": dt.datetime.utcnow().isoformat(),
                            "message": f"Progress advanced to {new_progress}% (simulation)",
                        })
                        summary["progressed"] += 1

                # persist updated metadata history
                job.extra_metadata = {**extra, "history": history}
                session.commit()
            except Exception as exc:  # pragma: no cover - defensive logging
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
