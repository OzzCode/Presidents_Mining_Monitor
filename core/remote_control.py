"""
Remote Control Service for Miners

Provides capabilities to remotely manage miners:
- Reboot miners
- Switch mining pools
- Power on/off (via schedule)
- Backup/restore configurations
- Bulk operations
"""

from __future__ import annotations
import datetime as dt
import time
import uuid
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from core.db import SessionLocal, CommandHistory, PowerSchedule, MinerConfigBackup, Miner
from core.miner import MinerClient
import logging

logger = logging.getLogger(__name__)


class RemoteControlService:
    """Service for remote miner management operations."""

    @staticmethod
    def reboot_miner(
            session: Session,
            miner_ip: str,
            initiated_by: str = 'system',
            batch_id: str = None
    ) -> CommandHistory:
        """
        Reboot a miner.
        
        Args:
            session: Database session
            miner_ip: IP address of miner
            initiated_by: Username or 'system'
            batch_id: Optional batch operation ID
            
        Returns:
            CommandHistory record
        """
        # Create command record
        cmd = CommandHistory(
            command_type='reboot',
            miner_ip=miner_ip,
            initiated_by=initiated_by,
            source='manual' if batch_id is None else 'bulk',
            batch_id=batch_id,
            status='pending'
        )
        session.add(cmd)
        session.commit()

        # Execute reboot
        start_time = dt.datetime.utcnow()
        cmd.sent_at = start_time

        try:
            client = MinerClient(miner_ip)
            # Use CGMiner restart command
            result = client.restart()

            cmd.status = 'success'
            cmd.response = {'result': result}
            cmd.completed_at = dt.datetime.utcnow()
            cmd.duration_ms = int((cmd.completed_at - start_time).total_seconds() * 1000)

            logger.info(f"Reboot successful for {miner_ip}")

        except Exception as e:
            cmd.status = 'failed'
            cmd.error_message = str(e)
            cmd.completed_at = dt.datetime.utcnow()
            cmd.duration_ms = int((cmd.completed_at - start_time).total_seconds() * 1000)

            logger.error(f"Reboot failed for {miner_ip}: {e}")

        session.commit()
        return cmd

    @staticmethod
    def bulk_reboot(
            session: Session,
            miner_ips: List[str],
            initiated_by: str = 'system'
    ) -> Dict:
        """
        Reboot multiple miners.
        
        Returns:
            Dict with keys: batch_id, total, successful, failed, commands
        """
        batch_id = str(uuid.uuid4())
        results = {
            'batch_id': batch_id,
            'total': len(miner_ips),
            'successful': 0,
            'failed': 0,
            'commands': []
        }

        for miner_ip in miner_ips:
            cmd = RemoteControlService.reboot_miner(
                session, miner_ip, initiated_by, batch_id
            )
            results['commands'].append({
                'miner_ip': miner_ip,
                'status': cmd.status,
                'error': cmd.error_message
            })

            if cmd.status == 'success':
                results['successful'] += 1
            else:
                results['failed'] += 1

        return results

    @staticmethod
    def switch_pool(
            session: Session,
            miner_ip: str,
            pool_url: str,
            worker_name: str,
            pool_password: str = 'x',
            pool_number: int = 0,
            initiated_by: str = 'system',
            batch_id: str = None
    ) -> CommandHistory:
        """
        Switch mining pool for a miner.
        
        Args:
            miner_ip: Miner IP address
            pool_url: New pool URL (e.g., "stratum+tcp://pool.example.com:3333")
            worker_name: Worker/username for pool
            pool_password: Pool password (default: 'x')
            pool_number: Pool number to update (0, 1, or 2)
            initiated_by: Username or 'system'
            batch_id: Optional batch operation ID
            
        Returns:
            CommandHistory record
            :param session:
        """
        params = {
            'pool_url': pool_url,
            'worker_name': worker_name,
            'pool_password': pool_password,
            'pool_number': pool_number
        }

        cmd = CommandHistory(
            command_type='pool_switch',
            miner_ip=miner_ip,
            parameters=params,
            initiated_by=initiated_by,
            source='manual' if batch_id is None else 'bulk',
            batch_id=batch_id,
            status='pending'
        )
        session.add(cmd)
        session.commit()

        start_time = dt.datetime.utcnow()
        cmd.sent_at = start_time

        try:
            client = MinerClient(miner_ip)

            # Remove old pool if exists
            try:
                client.remove_pool(pool_number)
            except:
                pass  # Pool might not exist

            # Add new pool
            result = client.add_pool(pool_url, worker_name, pool_password)

            # Switch to the new pool
            client.switch_pool(pool_number)

            # Update Miner metadata
            miner = session.query(Miner).filter(Miner.miner_ip == miner_ip).first()
            if miner:
                miner.pool_url = pool_url
                miner.worker_name = worker_name
                miner.pool_user = worker_name

            cmd.status = 'success'
            cmd.response = {'result': result}
            cmd.completed_at = dt.datetime.utcnow()
            cmd.duration_ms = int((cmd.completed_at - start_time).total_seconds() * 1000)

            logger.info(f"Pool switch successful for {miner_ip} to {pool_url}")

        except Exception as e:
            cmd.status = 'failed'
            cmd.error_message = str(e)
            cmd.completed_at = dt.datetime.utcnow()
            cmd.duration_ms = int((cmd.completed_at - start_time).total_seconds() * 1000)

            logger.error(f"Pool switch failed for {miner_ip}: {e}")

        session.commit()
        return cmd

    @staticmethod
    def bulk_pool_switch(
            session: Session,
            miner_ips: List[str],
            pool_url: str,
            worker_name: str,
            pool_password: str = 'x',
            initiated_by: str = 'system'
    ) -> Dict:
        """
        Switch pool for multiple miners.
        
        Returns:
            Dict with keys: batch_id, total, successful, failed, commands
        """
        batch_id = str(uuid.uuid4())
        results = {
            'batch_id': batch_id,
            'total': len(miner_ips),
            'successful': 0,
            'failed': 0,
            'commands': []
        }

        for miner_ip in miner_ips:
            cmd = RemoteControlService.switch_pool(
                session, miner_ip, pool_url, worker_name, pool_password,
                initiated_by=initiated_by, batch_id=batch_id
            )
            results['commands'].append({
                'miner_ip': miner_ip,
                'status': cmd.status,
                'error': cmd.error_message
            })

            if cmd.status == 'success':
                results['successful'] += 1
            else:
                results['failed'] += 1

        return results

    @staticmethod
    def backup_config(
            session: Session,
            miner_ip: str,
            backup_name: str = None,
            description: str = None,
            created_by: str = None
    ) -> MinerConfigBackup:
        """
        Backup miner configuration.
        
        Returns:
            MinerConfigBackup record
        """
        try:
            client = MinerClient(miner_ip)

            # Fetch configuration data
            stats = client.get_stats()
            pools = client.get_pools()
            try:
                version = client.get_version()
            except:
                version = None

            # Get miner metadata
            miner = session.query(Miner).filter(Miner.miner_ip == miner_ip).first()

            config_data = {
                'stats': stats,
                'pools': pools,
                'version': version,
                'timestamp': dt.datetime.utcnow().isoformat()
            }

            if not backup_name:
                backup_name = f"Auto backup {dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

            backup = MinerConfigBackup(
                miner_ip=miner_ip,
                model=miner.model if miner else None,
                firmware_version=miner.firmware_version if miner else None,
                backup_name=backup_name,
                description=description,
                backup_type='manual',
                config_data=config_data,
                created_by=created_by
            )

            session.add(backup)
            session.commit()

            logger.info(f"Config backup created for {miner_ip}")
            return backup

        except Exception as e:
            logger.error(f"Config backup failed for {miner_ip}: {e}")
            raise

    @staticmethod
    def get_command_history(
            session: Session,
            miner_ip: str = None,
            command_type: str = None,
            status: str = None,
            limit: int = 100
    ) -> List[CommandHistory]:
        """Get command history with optional filters."""
        query = session.query(CommandHistory)

        if miner_ip:
            query = query.filter(CommandHistory.miner_ip == miner_ip)
        if command_type:
            query = query.filter(CommandHistory.command_type == command_type)
        if status:
            query = query.filter(CommandHistory.status == status)

        return query.order_by(CommandHistory.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_config_backups(
            session: Session,
            miner_ip: str = None,
            limit: int = 50
    ) -> List[MinerConfigBackup]:
        """Get configuration backups."""
        query = session.query(MinerConfigBackup)

        if miner_ip:
            query = query.filter(MinerConfigBackup.miner_ip == miner_ip)

        return query.order_by(MinerConfigBackup.created_at.desc()).limit(limit).all()


class PowerScheduleService:
    """Service for managing power schedules."""

    @staticmethod
    def create_schedule(
            session: Session,
            name: str,
            schedule_type: str = 'weekly',
            weekly_schedule: List[Dict] = None,
            miner_ip: str = None,
            location: str = None,
            enabled: bool = True,
            created_by: str = None,
            **kwargs
    ) -> PowerSchedule:
        """Create a new power schedule."""
        schedule = PowerSchedule(
            name=name,
            schedule_type=schedule_type,
            weekly_schedule=weekly_schedule,
            miner_ip=miner_ip,
            location=location,
            enabled=enabled,
            created_by=created_by,
            **kwargs
        )

        session.add(schedule)
        session.commit()

        logger.info(f"Power schedule created: {name}")
        return schedule

    @staticmethod
    def get_active_schedules(
            session: Session,
            miner_ip: str = None,
            location: str = None
    ) -> List[PowerSchedule]:
        """Get active power schedules."""
        query = session.query(PowerSchedule).filter(PowerSchedule.enabled == True)

        if miner_ip:
            # Get schedules for this miner or fleet-wide schedules
            query = query.filter(
                or_(
                    PowerSchedule.miner_ip == miner_ip,
                    PowerSchedule.miner_ip.is_(None)
                )
            )

        if location:
            query = query.filter(
                or_(
                    PowerSchedule.location == location,
                    PowerSchedule.location.is_(None)
                )
            )

        return query.all()

    @staticmethod
    def should_be_powered_on(
            schedule: PowerSchedule,
            timestamp: dt.datetime = None
    ) -> bool:
        """
        Determine if miner should be powered on based on schedule.
        
        Returns:
            True if should be ON, False if should be OFF
        """
        if not timestamp:
            timestamp = dt.datetime.utcnow()

        if schedule.schedule_type == 'weekly':
            weekday = timestamp.weekday()  # Monday=0, Sunday=6
            hour = timestamp.hour

            if not schedule.weekly_schedule:
                return True  # No schedule = always on

            # Check if current time matches any OFF period
            for period in schedule.weekly_schedule:
                if period.get('action') != 'off':
                    continue

                if weekday in period.get('days', []):
                    start_h = period.get('start_hour', 0)
                    end_h = period.get('end_hour', 24)

                    # Handle periods that wrap around midnight
                    if start_h <= end_h:
                        if start_h <= hour < end_h:
                            return False  # Should be OFF
                    else:
                        if hour >= start_h or hour < end_h:
                            return False  # Should be OFF

            return True  # No OFF period matched, should be ON

        elif schedule.schedule_type == 'one-time':
            if schedule.one_time_start and schedule.one_time_end:
                if schedule.one_time_start <= timestamp <= schedule.one_time_end:
                    return schedule.one_time_action == 'on'
            return True  # Outside one-time window

        return True  # Default to ON

    @staticmethod
    def check_and_execute_schedules(session: Session) -> Dict:
        """
        Check all active schedules and execute power commands if needed.
        This should be called periodically (e.g., every minute) by scheduler.
        
        Returns:
            Dict with execution summary
        """
        schedules = PowerScheduleService.get_active_schedules(session)
        now = dt.datetime.utcnow()

        results = {
            'checked': len(schedules),
            'actions_taken': 0,
            'errors': 0
        }

        for schedule in schedules:
            try:
                should_be_on = PowerScheduleService.should_be_powered_on(schedule, now)

                # Get miners affected by this schedule
                if schedule.miner_ip:
                    miners = [schedule.miner_ip]
                elif schedule.location:
                    miner_records = session.query(Miner).filter(
                        Miner.location == schedule.location
                    ).all()
                    miners = [m.miner_ip for m in miner_records]
                else:
                    # Fleet-wide schedule
                    miner_records = session.query(Miner).all()
                    miners = [m.miner_ip for m in miner_records]

                # For each miner, check if action is needed
                # This is a placeholder - actual power on/off implementation
                # depends on miner capabilities (some miners don't support remote power control)
                # You might need to integrate with PDU (Power Distribution Unit) control

                # Log the schedule check
                logger.debug(f"Schedule '{schedule.name}': should_be_on={should_be_on}, affects {len(miners)} miners")

            except Exception as e:
                logger.error(f"Error executing schedule '{schedule.name}': {e}")
                results['errors'] += 1

        return results
