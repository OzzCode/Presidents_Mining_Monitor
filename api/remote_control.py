"""
API endpoints for remote miner management.

Provides endpoints for:
- Remote reboot
- Pool switching
- Configuration backup/restore
- Command history
- Power scheduling
"""

from flask import Blueprint, request, jsonify, g
from sqlalchemy import and_, func
from core.db import SessionLocal, CommandHistory, PowerSchedule, MinerConfigBackup, Miner
from core.remote_control import RemoteControlService, PowerScheduleService
import datetime as dt
from typing import List

bp = Blueprint("remote_control_api", __name__, url_prefix="/api/remote")


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
