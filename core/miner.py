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
        The command is newline-terminated and we read until we detect a newline
        (or null) or the peer closes the socket.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            # Connect
            sock.connect((self.ip, self.port))
            # CGMiner expects commands terminated by newline
            outgoing = (cmd.strip() + "\n").encode("utf-8")
            sock.sendall(outgoing)

            data = bytearray()
            while True:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    # If we've received nothing yet, propagate timeout so callers
                    # can handle it (and tests expecting socket.timeout still pass).
                    if not data:
                        raise
                    # If we have partial data, break and attempt to parse it.
                    break

                if not chunk:
                    # Peer closed connection
                    break

                data += chunk

                # Break on common terminators for CGMiner responses
                if b"\n" in chunk or b"\x00" in chunk:
                    break

            if not data:
                # No response data at all; raise timeout-like behavior
                raise socket.timeout("No data received from miner before timeout/close")

            # Extract first message line (before newline or null)
            raw = bytes(data)
            if b"\x00" in raw:
                raw = raw.split(b"\x00", 1)[0]
            if b"\n" in raw:
                first_line = raw.split(b"\n", 1)[0].decode("utf-8", errors="strict").strip()
            else:
                first_line = raw.decode("utf-8", errors="strict").strip()

            # Parse JSON; ValueError will propagate as desired by tests
            return json.loads(first_line)

        finally:
            try:
                sock.close()
            except Exception:
                pass

    def get_summary(self) -> dict:
        """Get overall summary (hashrate, temperatures, uptime, etc.)"""
        return self._send_command('summary')

    def get_stats(self) -> dict:
        """Get detailed stats for each chain."""
        return self._send_command('stats')

    def get_pools(self) -> dict:
        """Get mining pool information."""
        return self._send_command('pools')