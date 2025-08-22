import socket
import json
from config import CGMINER_TIMEOUT


class MinerError(Exception):
    pass


class MinerClient:
    """CGMiner API client for Antminer devices."""

    def __init__(self, ip, port=4028, timeout: float = None):
        self.ip = ip
        self.port = port
        self.timeout = timeout if timeout is not None else CGMINER_TIMEOUT

    def _send_command(self, cmd: str) -> dict:
        try:
            # Create connection with overall timeout (avoid context manager for test dummy sockets)
            with socket.create_connection((self.ip, self.port), self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall((cmd + " ").encode())
                chunks = []
                while True:
                    try:
                        chunk = sock.recv(4096)
                    except (socket.timeout, TimeoutError):
                        # stop reading on timeout; use what we have
                        break
                    if not chunk:
                        break
                    chunks.append(chunk)
            if not chunks:
                raise MinerError("No response from miner")
            raw = b''.join(chunks).decode(errors='ignore')
            # cgminer can send a single-line JSON, sometimes null-terminated
            line = raw.splitlines()[0] if " " in raw else raw.strip("�")

            return json.loads(line)

        except (socket.timeout, TimeoutError, ConnectionRefusedError, OSError, json.JSONDecodeError) as e:
            raise MinerError(f"CGMiner request failed: {e}")

    def get_summary(self) -> dict:
        return self._send_command('summary')

    def get_stats(self) -> dict:
        return self._send_command('stats')

    def get_pools(self) -> dict:
        return self._send_command('pools')
