import socket
import json


class MinerClient:
    """
    Client for communicating with an Antminer via the CGMiner/BMminer API.
    Uses JSON commands with a newline terminator and robust parsing to handle
    multi-chunk / null-terminated responses.
    """

    def __init__(self, ip, port=4028, timeout=8):
        self.ip = ip
        self.port = port
        self.timeout = timeout

    def _send_command(self, cmd: str) -> dict:
        """
        Send a command to the miner and return the parsed JSON response.
        Accepts either a bare command like "summary" or a JSON string.
        """
        # Wrap as JSON if the caller passed a bare command
        payload = cmd.strip()
        if not payload.startswith("{"):
            payload = json.dumps({"command": payload})

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        try:
            s.connect((self.ip, self.port))
            # Many firmwares require a newline to flush/terminate the command
            s.sendall((payload + "\n").encode("utf-8"))

            chunks = []
            while True:
                buf = s.recv(4096)
                if not buf:
                    break
                chunks.append(buf)

            text = b"".join(chunks).decode("utf-8", errors="ignore").strip()
            # bmminer often appends a trailing NUL; split on newlines and NULs
            candidates = [p for p in text.replace("\x00", "\n").splitlines() if p.strip()]

            # Try to parse each candidate until one succeeds
            for c in candidates:
                try:
                    return json.loads(c)
                except Exception:
                    continue

            # If we got here, nothing parsed as JSON
            raise ValueError(f"Unable to parse miner response: {text[:200]}")
        finally:
            try:
                s.close()
            except Exception:
                pass

    def get_summary(self) -> dict:
        """Get an overall summary (hashrate, uptime, etc.)."""
        return self._send_command("summary")

    def get_stats(self) -> dict:
        """Get detailed stats for chains (temps/fans often live here)."""
        return self._send_command("stats")

    def get_pools(self) -> dict:
        """Get mining pool information."""
        return self._send_command("pools")
