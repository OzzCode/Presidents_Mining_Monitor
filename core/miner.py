import socket
import json
import datetime as _dt
from config import CGMINER_TIMEOUT


class MinerError(Exception):
    pass


def _to_float(x):
    # noinspection PyBroadException
    try:
        return float(x)
    except Exception:
        return None


def _avg(seq):
    vals = [v for v in (_to_float(s) for s in seq) if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


class MinerClient:
    """CGMiner/BMminer API client for Antminer devices."""

    def __init__(self, ip, port=4028, timeout: float | None = None):
        self.ip = ip
        self.port = port
        self.timeout = timeout if timeout is not None else CGMINER_TIMEOUT

    def _send_command(self, cmd: str) -> dict:
        try:
            with socket.create_connection((self.ip, self.port), self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall((cmd + "\n").encode())
                chunks = []
                while True:
                    try:
                        chunk = sock.recv(4096)
                    except (socket.timeout, TimeoutError):
                        break  # stop reading on timeout; use what we have
                    if not chunk:
                        break
                    chunks.append(chunk)
            if not chunks:
                raise MinerError("No response from miner")
            raw = b"".join(chunks).decode(errors="ignore").strip("\x00\r\n ")
            line = raw.splitlines()[0] if "\n" in raw else raw
            return json.loads(line)
        except (socket.timeout, TimeoutError, ConnectionRefusedError, OSError, json.JSONDecodeError) as e:
            raise MinerError(f"CGMiner request failed: {e}")

    def get_summary(self) -> dict:
        return self._send_command("summary")

    def get_stats(self) -> dict:
        return self._send_command("stats")

    def get_pools(self) -> dict:
        return self._send_command("pools")

    # ---- Normalized view across SUMMARY/STATS ----
    def fetch_normalized(self) -> dict:
        """Return a normalized dict for dashboard & storage.

        Keys:
          hashrate_ths (float), elapsed_s (int), avg_temp_c (float),
          avg_fan_rpm (float), power_w (float), when (ISO8601 string)
        """
        summ = self.get_summary()  # {"SUMMARY":[{...}], "STATUS":[{...}]}
        try:
            stats = self.get_stats()  # {"STATS":[{...}, ...]}
        except MinerError:
            stats = {}

        s0 = (summ.get("SUMMARY") or [{}])[0]

        # Hashrate: prefer GHS, fallback to MHS
        ths = 0.0
        for k in ("GHS 5s", "GHS av", "GHS 1s", "MHS 5s", "MHS av", "MHS 1s"):
            if k in s0:
                val = _to_float(s0.get(k)) or 0.0
                ths = (val / 1000.0) if k.startswith("GHS") else (val / 1_000_000.0)
                break

        elapsed = int(_to_float(s0.get("Elapsed")) or 0)
        when_val = (summ.get("STATUS") or [{}])[0].get("When")
        if isinstance(when_val, (int, float)):
            when_iso = _dt.datetime.utcfromtimestamp(int(when_val)).isoformat() + "Z"
        else:
            when_iso = _dt.datetime.utcnow().isoformat() + "Z"

        temps, fans, powers = [], [], []
        for entry in (stats.get("STATS") or []):
            for key, val in entry.items():
                fv = _to_float(val)
                if fv is None:
                    continue
                lk = str(key).lower()
                if lk.startswith("temp"):
                    temps.append(fv)
                elif lk.startswith("fan"):
                    fans.append(fv)
                elif lk in ("power", "device power", "power_draw", "chain_power"):
                    powers.append(fv)

        return {
            "hashrate_ths": ths,
            "elapsed_s": elapsed,
            "avg_temp_c": _avg(temps),
            "avg_fan_rpm": _avg(fans),
            "power_w": sum(powers) if powers else 0.0,
            "when": when_iso,
        }
