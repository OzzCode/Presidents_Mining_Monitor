"""Firmware flashing utilities for various miner vendors.

This module provides vendor-specific implementations for flashing firmware to different
miner models. It handles the low-level details of the flashing process while providing
a consistent interface for the firmware service.
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import requests
from requests.auth import HTTPDigestAuth

from core.miner import MinerClient
from core.db import FirmwareFlashJob, FirmwareImage
from config import FIRMWARE_UPLOAD_DIR

logger = logging.getLogger(__name__)


class FlashError(Exception):
    """Base exception for all firmware flashing errors."""
    pass


class UnsupportedVendorError(FlashError):
    """Raised when a vendor is not supported."""
    pass


def get_flasher_for_miner(model: str, ip: str) -> 'BaseFlasher':
    """Factory function to get the appropriate flasher for a miner model.
    
    Args:
        model: Miner model (e.g., 'Antminer S19', 'Whatsminer M30S')
        ip: IP address of the miner
        
    Returns:
        An instance of the appropriate flasher class
        
    Raises:
        UnsupportedVendorError: If the vendor is not supported
    """
    model_lower = model.lower()

    if 'antminer' in model_lower or 'bitmain' in model_lower:
        return AntminerFlasher(ip)
    elif 'whatsminer' in model_lower or 'microbt' in model_lower:
        return WhatsminerFlasher(ip)
    elif 'avalon' in model_lower or 'canaan' in model_lower:
        return AvalonFlasher(ip)
    elif 'innosilicon' in model_lower:
        return InnosiliconFlasher(ip)
    else:
        raise UnsupportedVendorError(f"Unsupported miner model: {model}")


class BaseFlasher:
    """Base class for all firmware flashers."""

    def __init__(self, ip: str):
        self.ip = ip
        self.client = MinerClient(ip)
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for self-signed certs

    def check_prerequisites(self) -> Tuple[bool, str]:
        """Check if the miner is ready for flashing.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if miner is reachable
            stats = self.client.get_summary()
            if not stats:
                return False, "Failed to communicate with miner"

            # Check if miner is hashing
            if stats.get('ghs_5s', 0) > 0:
                return False, "Miner is currently hashing. Stop mining before flashing."

            return True, "Ready to flash"

        except Exception as e:
            return False, f"Error checking prerequisites: {str(e)}"

    def backup_config(self) -> Dict[str, Any]:
        """Back up miner configuration before flashing.
        
        Returns:
            Dictionary containing the backup data
        """
        try:
            # Default implementation - can be overridden by subclasses
            return {
                'summary': self.client.get_summary(),
                'pools': self.client.get_pools(),
                'timestamp': time.time(),
            }
        except Exception as e:
            logger.warning(f"Failed to back up config: {e}")
            return {}

    def flash(self, firmware_path: Path, progress_callback=None) -> Tuple[bool, str]:
        """Flash firmware to the miner.
        
        Args:
            firmware_path: Path to the firmware file
            progress_callback: Optional callback for progress updates (0-100)
            
        Returns:
            Tuple of (success, message)
        """
        raise NotImplementedError("Subclasses must implement flash()")

    def reboot(self) -> Tuple[bool, str]:
        """Reboot the miner after flashing.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            self.client.restart()
            return True, "Reboot command sent"
        except Exception as e:
            return False, f"Failed to reboot: {str(e)}"


class AntminerFlasher(BaseFlasher):
    """Flasher for Antminer devices."""

    def flash(self, firmware_path: Path, progress_callback=None) -> Tuple[bool, str]:
        """Flash firmware to an Antminer device."""
        try:
            if progress_callback:
                progress_callback(10, "Connecting to miner...")

            # Check if miner is ready
            ready, msg = self.check_prerequisites()
            if not ready:
                return False, f"Prerequisite check failed: {msg}"

            if progress_callback:
                progress_callback(20, "Backing up configuration...")

            # Backup config
            backup = self.backup_config()

            # Upload firmware
            url = f"http://{self.ip}/cgi-bin/upgrade.cgi"
            files = {'firmware': (firmware_path.name, open(firmware_path, 'rb'), 'application/octet-stream')}

            if progress_callback:
                progress_callback(40, "Uploading firmware...")

            response = self.session.post(
                url,
                files=files,
                auth=HTTPDigestAuth('root', 'root'),  # Default Antminer credentials
                timeout=300  # 5 minute timeout
            )

            if response.status_code != 200:
                return False, f"Failed to upload firmware: {response.text}"

            if progress_callback:
                progress_callback(80, "Verifying firmware...")

            # Wait for miner to process the firmware
            time.sleep(10)

            if progress_callback:
                progress_callback(90, "Rebooting miner...")

            # Reboot the miner
            success, msg = self.reboot()
            if not success:
                return False, f"Firmware uploaded but reboot failed: {msg}"

            return True, "Firmware update initiated successfully. The miner will reboot."

        except Exception as e:
            return False, f"Firmware update failed: {str(e)}"

        finally:
            # Clean up
            if 'files' in locals():
                files['firmware'][1].close()


class WhatsminerFlasher(BaseFlasher):
    """Flasher for Whatsminer devices."""

    def flash(self, firmware_path: Path, progress_callback=None) -> Tuple[bool, str]:
        """Flash firmware to a Whatsminer device."""
        try:
            if progress_callback:
                progress_callback(10, "Connecting to miner...")

            # Check if miner is ready
            ready, msg = self.check_prerequisites()
            if not ready:
                return False, f"Prerequisite check failed: {msg}"

            if progress_callback:
                progress_callback(20, "Backing up configuration...")

            # Backup config
            backup = self.backup_config()

            # Upload firmware
            url = f"http://{self.ip}/api/updateFirmware"
            files = {'file': (firmware_path.name, open(firmware_path, 'rb'))}

            if progress_callback:
                progress_callback(40, "Uploading firmware...")

            response = self.session.post(
                url,
                files=files,
                auth=('root', 'root'),  # Default Whatsminer credentials
                timeout=300  # 5 minute timeout
            )

            if response.status_code != 200 or not response.json().get('success', False):
                return False, f"Failed to upload firmware: {response.text}"

            if progress_callback:
                progress_callback(80, "Verifying firmware...")

            # Wait for miner to process the firmware
            time.sleep(10)

            if progress_callback:
                progress_callback(90, "Rebooting miner...")

            # Reboot the miner
            success, msg = self.reboot()
            if not success:
                return False, f"Firmware uploaded but reboot failed: {msg}"

            return True, "Firmware update initiated successfully. The miner will reboot."

        except Exception as e:
            return False, f"Firmware update failed: {str(e)}"

        finally:
            # Clean up
            if 'files' in locals():
                files['file'][1].close()


class AvalonFlasher(BaseFlasher):
    """Flasher for Avalon/Canaan devices."""

    def flash(self, firmware_path: Path, progress_callback=None) -> Tuple[bool, str]:
        """Flash firmware to an Avalon/Canaan device."""
        return False, "Avalon firmware flashing not yet implemented"


class InnosiliconFlasher(BaseFlasher):
    """Flasher for Innosilicon devices."""

    def flash(self, firmware_path: Path, progress_callback=None) -> Tuple[bool, str]:
        """Flash firmware to an Innosilicon device."""
        return False, "Innosilicon firmware flashing not yet implemented"
