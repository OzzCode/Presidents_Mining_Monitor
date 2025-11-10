"""
API endpoints for remote miner management.

Provides endpoints for:
- Remote reboot
- Pool switching
- Configuration backup/restore
- Command history
- Power scheduling
"""

import datetime as dt
import hashlib
import uuid
from pathlib import Path
from typing import List

from flask import Blueprint, request, jsonify, g, render_template
from sqlalchemy import and_, func
from werkzeug.utils import secure_filename

from config import (
    FIRMWARE_UPLOAD_DIR,
    MAX_FIRMWARE_SIZE_BYTES,
    FIRMWARE_ALLOWED_EXTENSIONS,
)
from core.db import (
    SessionLocal,
    CommandHistory,
    PowerSchedule,
    MinerConfigBackup,
    Miner,
    FirmwareImage,
)
from core.remote_control import RemoteControlService, PowerScheduleService
from core.firmware import FirmwareService, FirmwareFlashService

bp = Blueprint("remote_control_api", __name__, url_prefix="/api/remote")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _serialize_firmware_image(image: FirmwareImage) -> dict:
    return {
        "id": image.id,
        "file_name": image.file_name,
        "vendor": image.vendor,
        "model": image.model,
        "version": image.version,
        "checksum": image.checksum,
        "size_bytes": image.size_bytes,
        "uploaded_by": image.uploaded_by,
        "is_active": image.is_active,
        "created_at": image.created_at.isoformat() if image.created_at else None,
    }


def _serialize_flash_job(job, firmware: FirmwareImage | None = None) -> dict:
    firmware_payload = None
    if firmware:
        firmware_payload = {
            "id": firmware.id,
            "file_name": firmware.file_name,
            "version": firmware.version,
        }

    return {
        "job_id": job.job_id,
        "miner_ip": job.miner_ip,
        "status": job.status,
        "progress": job.progress,
        "initiated_by": job.initiated_by,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
        "metadata": job.extra_metadata or {},
        "firmware": firmware_payload,
    }


# ============================================================================
# Reboot Operations
# ============================================================================

@bp.route("/reboot/<miner_ip>", methods=["POST"])
def reboot_miner(miner_ip: str):
    """Reboot a single miner."""
    session = SessionLocal()
    try:
        username = getattr(g, 'user', None)
        initiated_by = username.username if username else 'anonymous'

        cmd = RemoteControlService.reboot_miner(
            session, miner_ip, initiated_by=initiated_by
        )

        return jsonify({
            "ok": True,
            "message": f"Reboot command sent to {miner_ip}",
            "command_id": cmd.id,
            "status": cmd.status
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/reboot/bulk", methods=["POST"])
def bulk_reboot():
    """Reboot multiple miners."""
    session = SessionLocal()
    try:
        data = request.json
        miner_ips = data.get("miner_ips", [])

        if not miner_ips:
            return jsonify({"ok": False, "error": "No miner IPs provided"}), 400

        username = getattr(g, 'user', None)
        initiated_by = username.username if username else 'anonymous'

        results = RemoteControlService.bulk_reboot(
            session, miner_ips, initiated_by=initiated_by
        )

        return jsonify({
            "ok": True,
            "message": f"Bulk reboot initiated for {results['total']} miners",
            "results": results
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


# ============================================================================
# Pool Switching
# ============================================================================

@bp.route("/pool/switch/<miner_ip>", methods=["POST"])
def switch_pool(miner_ip: str):
    """Switch mining pool for a single miner."""
    session = SessionLocal()
    try:
        data = request.json

        pool_url = data.get("pool_url")
        worker_name = data.get("worker_name")
        pool_password = data.get("pool_password", "x")
        pool_number = data.get("pool_number", 0)

        if not pool_url or not worker_name:
            return jsonify({
                "ok": False,
                "error": "pool_url and worker_name are required"
            }), 400

        username = getattr(g, 'user', None)
        initiated_by = username.username if username else 'anonymous'

        cmd = RemoteControlService.switch_pool(
            session, miner_ip, pool_url, worker_name, pool_password,
            pool_number, initiated_by=initiated_by
        )

        return jsonify({
            "ok": True,
            "message": f"Pool switch command sent to {miner_ip}",
            "command_id": cmd.id,
            "status": cmd.status
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/pool/switch/bulk", methods=["POST"])
def bulk_pool_switch():
    """Switch pool for multiple miners."""
    session = SessionLocal()
    try:
        data = request.json

        miner_ips = data.get("miner_ips", [])
        pool_url = data.get("pool_url")
        worker_name = data.get("worker_name")
        pool_password = data.get("pool_password", "x")

        if not miner_ips or not pool_url or not worker_name:
            return jsonify({
                "ok": False,
                "error": "miner_ips, pool_url, and worker_name are required"
            }), 400

        username = getattr(g, 'user', None)
        initiated_by = username.username if username else 'anonymous'

        results = RemoteControlService.bulk_pool_switch(
            session, miner_ips, pool_url, worker_name, pool_password,
            initiated_by=initiated_by
        )

        return jsonify({
            "ok": True,
            "message": f"Bulk pool switch initiated for {results['total']} miners",
            "results": results
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


# ============================================================================
# Configuration Backup/Restore
# ============================================================================

@bp.route("/backup/<miner_ip>", methods=["POST"])
def backup_config(miner_ip: str):
    """Create a configuration backup for a miner."""
    session = SessionLocal()
    try:
        data = request.json or {}
        backup_name = data.get("backup_name")
        description = data.get("description")

        username = getattr(g, 'user', None)
        created_by = username.username if username else 'anonymous'

        backup = RemoteControlService.backup_config(
            session, miner_ip, backup_name, description, created_by
        )

        return jsonify({
            "ok": True,
            "message": f"Configuration backup created for {miner_ip}",
            "backup_id": backup.id,
            "backup_name": backup.backup_name
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/backups", methods=["GET"])
def list_backups():
    """List configuration backups."""
    session = SessionLocal()
    try:
        miner_ip = request.args.get("miner_ip")
        limit = int(request.args.get("limit", 50))

        backups = RemoteControlService.get_config_backups(session, miner_ip, limit)

        return jsonify({
            "ok": True,
            "backups": [
                {
                    "id": b.id,
                    "miner_ip": b.miner_ip,
                    "backup_name": b.backup_name,
                    "description": b.description,
                    "backup_type": b.backup_type,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                    "created_by": b.created_by,
                    "model": b.model,
                    "firmware_version": b.firmware_version,
                    "is_validated": b.is_validated
                }
                for b in backups
            ],
            "count": len(backups)
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/backups/<int:backup_id>", methods=["GET"])
def get_backup(backup_id: int):
    """Get a specific backup with full configuration data."""
    session = SessionLocal()
    try:
        backup = session.query(MinerConfigBackup).filter(
            MinerConfigBackup.id == backup_id
        ).first()

        if not backup:
            return jsonify({"ok": False, "error": "Backup not found"}), 404

        return jsonify({
            "ok": True,
            "backup": {
                "id": backup.id,
                "miner_ip": backup.miner_ip,
                "backup_name": backup.backup_name,
                "description": backup.description,
                "backup_type": backup.backup_type,
                "created_at": backup.created_at.isoformat() if backup.created_at else None,
                "created_by": backup.created_by,
                "model": backup.model,
                "firmware_version": backup.firmware_version,
                "config_data": backup.config_data,
                "is_validated": backup.is_validated
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


# ============================================================================
# Command History
# ============================================================================

@bp.route("/commands/history", methods=["GET"])
def get_command_history():
    """Get command execution history."""
    session = SessionLocal()
    try:
        miner_ip = request.args.get("miner_ip")
        command_type = request.args.get("command_type")
        status = request.args.get("status")
        limit = int(request.args.get("limit", 100))

        commands = RemoteControlService.get_command_history(
            session, miner_ip, command_type, status, limit
        )

        return jsonify({
            "ok": True,
            "commands": [
                {
                    "id": cmd.id,
                    "timestamp": cmd.timestamp.isoformat() if cmd.timestamp else None,
                    "command_type": cmd.command_type,
                    "miner_ip": cmd.miner_ip,
                    "status": cmd.status,
                    "parameters": cmd.parameters,
                    "error_message": cmd.error_message,
                    "initiated_by": cmd.initiated_by,
                    "source": cmd.source,
                    "batch_id": cmd.batch_id,
                    "duration_ms": cmd.duration_ms,
                    "sent_at": cmd.sent_at.isoformat() if cmd.sent_at else None,
                    "completed_at": cmd.completed_at.isoformat() if cmd.completed_at else None
                }
                for cmd in commands
            ],
            "count": len(commands)
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/commands/stats", methods=["GET"])
def get_command_stats():
    """Get command execution statistics."""
    session = SessionLocal()
    try:
        # Get stats for last 24 hours
        since = dt.datetime.utcnow() - dt.timedelta(hours=24)

        total = session.query(func.count(CommandHistory.id)).filter(
            CommandHistory.timestamp >= since
        ).scalar()

        successful = session.query(func.count(CommandHistory.id)).filter(
            and_(
                CommandHistory.timestamp >= since,
                CommandHistory.status == 'success'
            )
        ).scalar()

        failed = session.query(func.count(CommandHistory.id)).filter(
            and_(
                CommandHistory.timestamp >= since,
                CommandHistory.status == 'failed'
            )
        ).scalar()

        # Get command type breakdown
        by_type = session.query(
            CommandHistory.command_type,
            func.count(CommandHistory.id).label('count')
        ).filter(
            CommandHistory.timestamp >= since
        ).group_by(CommandHistory.command_type).all()

        return jsonify({
            "ok": True,
            "stats": {
                "period": "last_24_hours",
                "total": total or 0,
                "successful": successful or 0,
                "failed": failed or 0,
                "pending": (total or 0) - (successful or 0) - (failed or 0),
                "by_type": {
                    cmd_type: count for cmd_type, count in by_type
                }
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


# ============================================================================
# Power Scheduling
# ============================================================================

@bp.route("/schedule/power", methods=["GET"])
def list_power_schedules():
    """List power schedules."""
    session = SessionLocal()
    try:
        enabled_only = request.args.get("enabled_only", "false").lower() == "true"

        query = session.query(PowerSchedule)
        if enabled_only:
            query = query.filter(PowerSchedule.enabled == True)

        schedules = query.order_by(PowerSchedule.created_at.desc()).all()

        return jsonify({
            "ok": True,
            "schedules": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "enabled": s.enabled,
                    "schedule_type": s.schedule_type,
                    "miner_ip": s.miner_ip,
                    "location": s.location,
                    "weekly_schedule": s.weekly_schedule,
                    "one_time_start": s.one_time_start.isoformat() if s.one_time_start else None,
                    "one_time_end": s.one_time_end.isoformat() if s.one_time_end else None,
                    "power_limit_w": s.power_limit_w,
                    "timezone": s.timezone,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "created_by": s.created_by
                }
                for s in schedules
            ],
            "count": len(schedules)
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/schedule/power", methods=["POST"])
def create_power_schedule():
    """Create a new power schedule."""
    session = SessionLocal()
    try:
        data = request.json

        username = getattr(g, 'user', None)
        created_by = username.username if username else 'anonymous'

        schedule = PowerScheduleService.create_schedule(
            session,
            name=data["name"],
            schedule_type=data.get("schedule_type", "weekly"),
            weekly_schedule=data.get("weekly_schedule"),
            miner_ip=data.get("miner_ip"),
            location=data.get("location"),
            enabled=data.get("enabled", True),
            description=data.get("description"),
            power_limit_w=data.get("power_limit_w"),
            timezone=data.get("timezone", "UTC"),
            electricity_rate_id=data.get("electricity_rate_id"),
            created_by=created_by
        )

        return jsonify({
            "ok": True,
            "message": "Power schedule created",
            "schedule_id": schedule.id
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/schedule/power/<int:schedule_id>", methods=["PUT"])
def update_power_schedule(schedule_id: int):
    """Update a power schedule."""
    session = SessionLocal()
    try:
        schedule = session.query(PowerSchedule).filter(
            PowerSchedule.id == schedule_id
        ).first()

        if not schedule:
            return jsonify({"ok": False, "error": "Schedule not found"}), 404

        data = request.json

        for field in ["name", "description", "enabled", "schedule_type",
                      "weekly_schedule", "miner_ip", "location", "power_limit_w",
                      "timezone", "electricity_rate_id"]:
            if field in data:
                setattr(schedule, field, data[field])

        schedule.updated_at = dt.datetime.utcnow()
        session.commit()

        return jsonify({
            "ok": True,
            "message": "Power schedule updated"
        })

    except Exception as e:
        session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/schedule/power/<int:schedule_id>", methods=["DELETE"])
def delete_power_schedule(schedule_id: int):
    """Delete a power schedule."""
    session = SessionLocal()
    try:
        schedule = session.query(PowerSchedule).filter(
            PowerSchedule.id == schedule_id
        ).first()

        if not schedule:
            return jsonify({"ok": False, "error": "Schedule not found"}), 404

        session.delete(schedule)
        session.commit()

        return jsonify({
            "ok": True,
            "message": "Power schedule deleted"
        })

    except Exception as e:
        session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/schedule/power/<int:schedule_id>/toggle", methods=["POST"])
def toggle_power_schedule(schedule_id: int):
    """Enable/disable a power schedule."""
    session = SessionLocal()
    try:
        schedule = session.query(PowerSchedule).filter(
            PowerSchedule.id == schedule_id
        ).first()

        if not schedule:
            return jsonify({"ok": False, "error": "Schedule not found"}), 404

        schedule.enabled = not schedule.enabled
        schedule.updated_at = dt.datetime.utcnow()
        session.commit()

        return jsonify({
            "ok": True,
            "message": f"Schedule {'enabled' if schedule.enabled else 'disabled'}",
            "enabled": schedule.enabled
        })

    except Exception as e:
        session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


@bp.route("/schedule/check", methods=["POST"])
def check_schedules():
    """Manually trigger schedule check and execution."""
    session = SessionLocal()
    try:
        results = PowerScheduleService.check_and_execute_schedules(session)

        return jsonify({
            "ok": True,
            "message": "Schedule check completed",
            "results": results
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        session.close()


# ============================================================================
# HTML PAGE ROUTE
# ============================================================================

@bp.route('/page', methods=['GET'])
def remote_control_page():
    """Render the remote control dashboard HTML page."""
    return render_template('remote_control.html')


# ============================================================================
# Firmware Flashing (Scaffold)
# ============================================================================


@bp.route('/firmware/images', methods=['GET'])
def list_firmware_images():
    """List available firmware images."""
    session = SessionLocal()
    try:
        images = FirmwareService.list_images(session)
        return jsonify({
            "ok": True,
            "images": [_serialize_firmware_image(image) for image in images]
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        session.close()


@bp.route('/firmware/upload', methods=['POST'])
def upload_firmware_image():
    """Upload a firmware image and register its metadata."""
    session = SessionLocal()
    try:
        if 'file' not in request.files:
            return jsonify({"ok": False, "error": "No file provided"}), 400

        file_storage = request.files['file']
        if not file_storage or not file_storage.filename:
            return jsonify({"ok": False, "error": "Filename is required"}), 400

        original_name = file_storage.filename
        filename = secure_filename(original_name)
        if not filename:
            return jsonify({"ok": False, "error": "Invalid filename"}), 400

        lower_name = filename.lower()
        if not any(
                lower_name.endswith(f".{ext}")
                for ext in FIRMWARE_ALLOWED_EXTENSIONS
        ):
            return jsonify({"ok": False, "error": "Unsupported file extension"}), 400

        file_bytes = file_storage.read()
        size_bytes = len(file_bytes)
        if size_bytes == 0:
            return jsonify({"ok": False, "error": "File is empty"}), 400
        if size_bytes > MAX_FIRMWARE_SIZE_BYTES:
            return jsonify({"ok": False, "error": "File exceeds maximum allowed size"}), 400

        checksum = hashlib.sha256(file_bytes).hexdigest()

        existing = session.query(FirmwareImage).filter(FirmwareImage.checksum == checksum).first()
        if existing:
            return jsonify({
                "ok": True,
                "message": "Firmware already uploaded",
                "duplicate": True,
                "image": _serialize_firmware_image(existing),
            }), 200

        unique_name = f"{uuid.uuid4().hex}_{filename}"
        storage_path = Path(FIRMWARE_UPLOAD_DIR) / unique_name
        with open(storage_path, 'wb') as fh:
            fh.write(file_bytes)

        username = getattr(g, 'user', None)
        uploaded_by = username.username if username else 'anonymous'

        metadata = {
            'file_name': filename,
            'storage_path': str(storage_path.resolve()),
            'checksum': checksum,
            'size_bytes': size_bytes,
            'vendor': request.form.get('vendor') or None,
            'model': request.form.get('model') or None,
            'version': request.form.get('version') or None,
            'notes': request.form.get('notes') or None,
            'uploaded_by': uploaded_by,
        }

        image = FirmwareService.create_image(session, **metadata)

        return jsonify({
            "ok": True,
            "message": "Firmware uploaded",
            "image": _serialize_firmware_image(image)
        }), 201
    except Exception as exc:
        session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        session.close()


@bp.route('/firmware/jobs', methods=['POST'])
def create_firmware_flash_job():
    """Create a firmware flash job placeholder."""
    session = SessionLocal()
    try:
        data = request.json or {}
        firmware_id = data.get('firmware_id')
        miner_ips = data.get('miner_ips') or []

        if not firmware_id:
            return jsonify({"ok": False, "error": "firmware_id is required"}), 400
        if not miner_ips:
            return jsonify({"ok": False, "error": "miner_ips is required"}), 400

        firmware = FirmwareService.get_image(session, firmware_id)
        if firmware and not firmware.is_active:
            firmware = None
        if not firmware:
            return jsonify({"ok": False, "error": "Firmware image not found or inactive"}), 404

        username = getattr(g, 'user', None)
        initiated_by = username.username if username else 'anonymous'

        jobs = []
        for miner_ip in miner_ips:
            job = FirmwareFlashService.create_job(
                session,
                firmware_id=firmware.id,
                miner_ip=miner_ip,
                initiated_by=initiated_by,
                metadata={"request_source": "api"},
            )
            jobs.append(_serialize_flash_job(job, firmware))

        return jsonify({
            "ok": True,
            "message": f"Created {len(jobs)} firmware flash jobs",
            "jobs": jobs,
        }), 201
    except Exception as exc:
        session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        session.close()


@bp.route('/firmware/jobs', methods=['GET'])
def list_firmware_flash_jobs():
    """List recent firmware flash jobs."""
    session = SessionLocal()
    try:
        miner_ip = request.args.get('miner_ip')
        jobs = FirmwareFlashService.list_jobs(session, miner_ip=miner_ip)

        firmware_map = {}
        for job in jobs:
            if job.firmware_id not in firmware_map:
                firmware_map[job.firmware_id] = FirmwareService.get_image(session, job.firmware_id)

        return jsonify({
            "ok": True,
            "jobs": [
                _serialize_flash_job(job, firmware_map.get(job.firmware_id))
                for job in jobs
            ]
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        session.close()


@bp.route('/firmware/jobs/<job_id>', methods=['GET'])
def get_firmware_flash_job(job_id: str):
    """Retrieve status for a firmware flash job."""
    session = SessionLocal()
    try:
        job = FirmwareFlashService.get_job_by_public_id(session, job_id)
        if not job:
            return jsonify({"ok": False, "error": "Job not found"}), 404

        firmware = FirmwareService.get_image(session, job.firmware_id)
        return jsonify({
            "ok": True,
            "job": _serialize_flash_job(job, firmware)
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        session.close()
