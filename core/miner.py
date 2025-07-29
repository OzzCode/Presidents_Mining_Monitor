import socket
import json


class MinerClient:
    """
    Client for communicating with an Antminer via the CGMiner API.
    """

    def __init__(self, ip, port=4028, timeout=5):
        self.ip = ip
        self.port = port
        self.timeout = timeout

    def _send_command(self, cmd: str) -> dict:
        """
        Send a command to the CGMiner API and return the parsed JSON response.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.ip, self.port))
            # CGMiner expects commands terminated by newline
            sock.sendall((cmd.strip() + "").encode('utf-8'))
            data = b''
            # Read until the socket closes
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk

            text = data.decode('utf-8').strip()
            # CGMiner responses may include multiple JSON objects; take the first
            first_line = text.splitlines()[0]
            return json.loads(first_line)
        finally:
            sock.close()

    def get_summary(self) -> dict:
        """Get overall summary (hashrate, temperatures, uptime, etc.)"""
        return self._send_command('summary')

    def get_stats(self) -> dict:
        """Get detailed stats for each chain."""
        return self._send_command('stats')

    def get_pools(self) -> dict:
        """Get mining pool information."""
        return self._send_command('pools')
