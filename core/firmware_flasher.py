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


def _is_hashing(summary: Dict[str, Any]) -> bool:
    """Heuristic to determine if a miner is actively hashing from a summary dict."""
    if not isinstance(summary, dict):
        return False
    keys = ('ghs_5s', 'GHS 5s', 'hashrate_5s', 'ghs_1m', 'GH S 5s')
    for k in keys:
        v = summary.get(k)
        try:
            if v is None:
                continue
            if float(v) > 0:
                return True
        except Exception:
            continue
    return False


class BaseFlasher:
    """Base class for all firmware flashers."""

    def __init__(self, ip: str, *, auth=None, verify: bool = False, timeout: int = 300):
        self.ip = ip
        self.client = MinerClient(ip)
        self.session = requests.Session()
        # Accept runtime injection for TLS verify; default False for miner self-signed certs
        self.session.verify = verify
        # Requests auth object or (user, password) tuple
        self.auth = auth
        # Default request timeout in seconds
        self.timeout = timeout

    @staticmethod
    def build_auth(auth_mode: Optional[str], user: Optional[str], password: Optional[str]):
        """Construct a requests-compatible auth object from config values."""
        if not user:
            return None
        mode = (auth_mode or '').lower()
        if mode == 'digest':
            return HTTPDigestAuth(user, password or '')
        # default/basic
        return (user, password or '')

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

            # Check if miner is hashing and try to auto-stop if supported
            if _is_hashing(stats):
                try:
                    if hasattr(self.client, 'stop_mining'):
                        self.client.stop_mining()
                    elif hasattr(self.client, 'pause_mining'):
                        self.client.pause_mining()
                    # give the miner a moment to settle
                    time.sleep(2)
                    stats2 = self.client.get_summary()
                    if _is_hashing(stats2):
                        return False, "Unable to auto-stop mining; please stop mining manually and retry."
                except Exception as e:
                    return False, f"Error attempting to stop mining: {str(e)}"

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
            if progress_callback:
                progress_callback(40, "Uploading firmware...")

            with open(firmware_path, 'rb') as fh:
                files = {'firmware': (firmware_path.name, fh, 'application/octet-stream')}
                response = self.session.post(
                    url,
                    files=files,
                    auth=self.auth,
                    timeout=self.timeout,
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
            if progress_callback:
                progress_callback(40, "Uploading firmware...")

            with open(firmware_path, 'rb') as fh:
                files = {'file': (firmware_path.name, fh)}
                response = self.session.post(
                    url,
                    files=files,
                    auth=self.auth,
                    timeout=self.timeout,
                )

            if response.status_code != 200:
                return False, f"Failed to upload firmware (HTTP {response.status_code}): {response.text[:200]}"
            ok = False
            try:
                if 'application/json' in (response.headers.get('Content-Type') or ''):
                    ok = bool(response.json().get('success', False))
            except Exception:
                ok = False
            if not ok:
                return False, f"Unexpected response from miner: {response.text[:200]}"

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
            pass


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
