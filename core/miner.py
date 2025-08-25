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
        """
        Send a JSON command (with a newline terminator) and parse a robust response.
        """
        import json, socket
        payload = cmd.strip()
        if not payload.startswith("{"):
            payload = json.dumps({"command": payload})

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        try:
            s.connect((self.ip, self.port))
            s.sendall((payload + "\n").encode("utf-8"))  # <-- newline is critical

            chunks = []
            while True:
                buf = s.recv(4096)
                if not buf:
                    break
                chunks.append(buf)

            text = b"".join(chunks).decode("utf-8", errors="ignore").strip()
            # bmminer sometimes adds NULs; split by newlines/NULs and parse first valid JSON
            for line in [p for p in text.replace("\x00", "\n").splitlines() if p.strip()]:
                try:
                    return json.loads(line)
                except Exception:
                    continue
            raise ValueError(f"Unable to parse miner response: {text[:200]}")
        finally:
            try:
                s.close()
            except Exception:
                pass

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
