import datetime as _dt
from config import CGMINER_TIMEOUT, EFFICIENCY_J_PER_TH
from helpers.utils import efficiency_for_model

HASHRATE_KEYS = [
    ("GHS 5s", "GHS"), ("GHS av", "GHS"),
    ("GHS 1s", "GHS"), ("MHS 5s", "MHS"),
    ("MHS av", "MHS"), ("MHS 1s", "MHS")
]


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

    def __init__(self, ip, port=4028, timeout: float = None):
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
            # bmminer sometimes adds NULs; split by newlines/NULs and parse the first valid JSON
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

    # ---- Normalized view across SUMMARY/STATS ----
    def fetch_normalized(self) -> dict:
        """Return a normalized dict for dashboard & storage.

        Keys:
          hashrate_ths (float), elapsed_s (int), avg_temp_c (float),
          avg_fan_rpm (float), power_w (float), when (ISO8601 string)
        """
        try:
            summ = self.get_summary()  # {"SUMMARY":[{...}], "STATUS":[{...}]}
        except Exception as e:
            # Normalize any parsing/IO error to MinerError for callers that expect it
            raise MinerError(str(e))
        try:
            stats = self.get_stats()  # {"STATS":[{...}, ...]}
        except Exception:
            stats = {}
        try:
            ver = self.get_version()  # {"VERSION":[{...}], "STATUS":[{...}]}, varies by FW
        except Exception:
            ver = {}

        s0 = (summ.get("SUMMARY") or [{}])[0]

        # determine model (robust across firmware variants)
        def _norm_model(m):
            if not m:
                return ""
            m = str(m).strip()
            # common cleanup
            m = " ".join(m.split())
            return m

        def _walk_for_model(obj):
            # Look for common keys across SUMMARY/STATS/VERSION
            MODEL_KEYS = {
                "model", "type", "miner type", "minertype",
                "modelname", "miner name", "product type", "product", "hw type"
            }
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        res = _walk_for_model(v)
                        if res:
                            return res
                    key = str(k).strip().lower()
                    if key in MODEL_KEYS:
                        if isinstance(v, str) and v.strip():
                            return v
                return None
            if isinstance(obj, list):
                for it in obj:
                    res = _walk_for_model(it)
                    if res:
                        return res
                return None
            return None

        # Try explicit places first, then recursive scan:
        candidates = []

        # some firmwares expose 'Model' at top-level or inside SUMMARY[0]
        candidates.append(summ.get("Model"))
        candidates.append(s0.get("Model"))
        candidates.append(s0.get("Type"))  # SUMMARY sometimes has "Type": "Antminer S19 Pro"

        # stats blocks sometimes have "Type"/"Model"/"ModelName"
        for entry in (stats.get("STATS") or []):
            candidates.append(entry.get("Model"))
            candidates.append(entry.get("ModelName"))
            candidates.append(entry.get("Type"))
            # Some expose with spaces/case differences
            candidates.append(entry.get("Miner Name"))
            candidates.append(entry.get("MinerType"))
            candidates.append(entry.get("Product Type"))

        # version often has "Type" or similar in VERSION[0]
        v0 = (ver.get("VERSION") or [{}])[0] if isinstance(ver, dict) else {}
        candidates.append(ver.get("Model"))
        candidates.append(v0.get("Model"))
        candidates.append(v0.get("Type"))
        candidates.append(v0.get("MinerType"))
        candidates.append(v0.get("Miner Name"))

        # fallback: recursively walk for common model keys
        if not any(candidates):
            candidates.append(_walk_for_model(summ))
            candidates.append(_walk_for_model(stats))
            candidates.append(_walk_for_model(ver))

        model = next((m for m in candidates if isinstance(m, str) and m.strip()), "")
        model = _norm_model(model)

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

        j_per_th = efficiency_for_model(model)
        power_w = ths * (j_per_th or EFFICIENCY_J_PER_TH)

        return {
            "hashrate_ths": ths,
            "elapsed_s": elapsed,
            "avg_temp_c": _avg(temps),
            "avg_fan_rpm": _avg(fans),
            # Ignore live powers[], always estimate:
            "power_w": power_w,
            "when": when_iso,
            "model": model or "",
        }

    def get_summary(self) -> dict:
        return self._send_command("summary")

    def get_stats(self) -> dict:
        return self._send_command("stats")

    def get_pools(self) -> dict:
        return self._send_command("pools")

    def get_notify(self) -> dict:
        return self._send_command("notify")

    def get_log(self) -> dict:
        # some firmwares expose 'log' or 'readlog'; try 'log' first
        return self._send_command("log")

    def get_version(self) -> dict:
        return self._send_command("version")

    # ---- Pool management ----
    def add_pool(self, url: str, username: str, password: str = "") -> dict:
        """
        Add a new pool via CGMiner/BMminer API.
        Equivalent to: {"command":"addpool","parameter":"url,user,pass"}
        Password may be empty for pools that don't require it.
        """
        import json
        url = (url or "").strip()
        username = (username or "").strip()
        password = "" if password is None else str(password)
        if not url or not username:
            raise MinerError("url and username are required to add a pool")
        # The API expects a single string parameter: "url,user,pass"
        param = f"{url},{username},{password}"
        payload = json.dumps({"command": "addpool", "parameter": param})
        return self._send_command(payload)

    def pool_priority(self, priority_list: list[int]) -> dict:
        """
        Optionally set pool priorities. Expects a list like [0,1,2].
        Maps to command: {"command":"poolpriority","parameter":"0,1,2"}
        """
        import json
        if not priority_list:
            raise MinerError("priority_list cannot be empty")
        param = ",".join(str(int(i)) for i in priority_list)
        payload = json.dumps({"command": "poolpriority", "parameter": param})
        return self._send_command(payload)

    def remove_pool(self, pool_id: int) -> dict:
        """
        Remove a pool by its index/id as reported by the miner (CGMiner/BMminer).
        Example payload: {"command":"removepool","parameter":"0"}
        """
        import json
        try:
            pid = int(pool_id)
        except Exception:
            raise MinerError("pool_id must be an integer")
        payload = json.dumps({"command": "removepool", "parameter": str(pid)})
        return self._send_command(payload)

    def list_pool_ids(self) -> list[int]:
        """Return a list of current pool indices as integers, best-effort across firmwares."""
        try:
            resp = self.get_pools() or {}
        except Exception as e:
            raise MinerError(f"failed to get pools: {e}")
        pools = resp.get("POOLS") or resp.get("pools") or []
        ids = []
        for p in pools if isinstance(pools, list) else []:
            for key in ("POOL", "Index", "POOL#", "ID", "id"):
                if key in p:
                    try:
                        ids.append(int(p[key]))
                        break
                    except Exception:
                        continue
        # de-dup and sort
        ids = sorted({i for i in ids if isinstance(i, int)})
        return ids

    # ---- Remote control commands ----
    def restart(self) -> dict:
        """
        Reboot the miner using its web interface where possible.
        Tries a variety of common vendor endpoints (Antminer/BOSMiner/VNish/etc.).
        Falls back to CGMiner 'restart' (software only) if device reboot endpoints fail.
        """
        import requests
        from requests.auth import HTTPDigestAuth
        from config import MINER_USERNAME, MINER_PASSWORD

        # Try configured credentials first, then common defaults
        credentials = [
            (MINER_USERNAME, MINER_PASSWORD),  # From config/env
            ("admin", "admin"),  # VNish common default
            ("root", "root"),
            ("root", "admin"),
        ]

        # Endpoint candidates: (method, path, data, headers)
        # Note: Many firmwares show a confirmation page at GET /cgi-bin/reboot.cgi (200)
        # and only reboot when a subsequent POST/GET with a query param is sent.
        candidates = [
            # VNish/Antminer typical form submits
            ("POST", "/cgi-bin/reboot.cgi", {"reboot": "Reboot"}, None),
            ("POST", "/cgi-bin/reboot.cgi", {"reboot": "1"}, None),
            ("POST", "/cgi-bin/reboot.cgi", {"confirm": "1"}, None),
            # VNish often uses a JS confirm that hits reboot.cgi?reboot=yes
            ("GET", "/cgi-bin/reboot.cgi?reboot=yes", None, None),
            ("GET", "/cgi-bin/reboot.cgi?confirm=1", None, None),
            ("GET", "/cgi-bin/reboot.cgi?reboot=1", None, None),
            # Other common variants
            ("POST", "/cgi-bin/system.cgi", {"action": "reboot"}, None),
            ("POST", "/cgi-bin/restart.cgi", None, None),
            ("POST", "/api/reboot", None, {"Content-Type": "application/json"}),
            # As a last detection step only, fetch the page (but do not treat 200 as success)
            ("GET", "/cgi-bin/reboot.cgi", None, None),
        ]

        acceptable = {200, 204, 301, 302, 303, 307, 308}
        last_error = None

        try:
            s = requests.Session()
        except Exception:
            # session creation should not block; fallback to direct requests
            s = None

        def _request(method, url, **kwargs):
            if s is not None:
                return s.request(method, url, **kwargs)
            import requests as _r
            return _r.request(method, url, **kwargs)

        for username, password in credentials:
            # Try with Digest first, then Basic
            auth_methods = [HTTPDigestAuth(username, password), (username, password)]
            for auth in auth_methods:
                https_hint = False
                # First pass: attempt explicit reboot actions, skip the plain GET success
                for method, path, data, headers in candidates:
                    url = f"http://{self.ip}{path}"
                    try:
                        resp = _request(
                            method,
                            url,
                            timeout=8,
                            auth=auth,
                            data=data,
                            headers=headers,
                            allow_redirects=False,
                        )
                        # Detect HTTP->HTTPS redirect hints
                        if resp.status_code in (301, 308) and (
                            resp.headers.get("Location", "").startswith("https://")
                        ):
                            https_hint = True
                        # Treat acceptance only for actions that actually trigger reboot
                        triggers_reboot = not (method == "GET" and path == "/cgi-bin/reboot.cgi")
                        if triggers_reboot and resp.status_code in acceptable:
                            return {
                                "STATUS": [{
                                    "STATUS": "S",
                                    "When": 0,
                                    "Code": 0,
                                    "Msg": f"Reboot command accepted via {path} ({method})"
                                }],
                                "id": 1
                            }
                        # 401/403 -> wrong credentials/auth type; try next
                        if resp.status_code in (401, 403):
                            continue
                    except requests.exceptions.Timeout:
                        # Timeouts commonly happen when the device starts rebooting
                        return {
                            "STATUS": [{
                                "STATUS": "S",
                                "When": 0,
                                "Code": 0,
                                "Msg": "Reboot initiated (timeout while applying command)"
                            }],
                            "id": 1
                        }
                    except requests.exceptions.ConnectionError:
                        # Connection drop is typical immediately after reboot is triggered
                        return {
                            "STATUS": [{
                                "STATUS": "S",
                                "When": 0,
                                "Code": 0,
                                "Msg": "Reboot initiated (connection dropped)"
                            }],
                            "id": 1
                        }
                    except Exception as e:
                        last_error = str(e)
                        continue

                # If server indicated HTTPS is required, retry with https:// for trigger endpoints
                if https_hint:
                    for method, path, data, headers in candidates:
                        if method == "GET" and path == "/cgi-bin/reboot.cgi":
                            continue  # skip non-trigger page
                        url = f"https://{self.ip}{path}"
                        try:
                            resp = _request(
                                method,
                                url,
                                timeout=8,
                                auth=auth,
                                data=data,
                                headers=headers,
                                allow_redirects=False,
                                verify=False,  # many miner UIs use self-signed certs
                            )
                            if resp.status_code in acceptable:
                                return {
                                    "STATUS": [{
                                        "STATUS": "S",
                                        "When": 0,
                                        "Code": 0,
                                        "Msg": f"Reboot command accepted via {path} ({method}) over HTTPS"
                                    }],
                                    "id": 1
                                }
                        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                            return {
                                "STATUS": [{
                                    "STATUS": "S",
                                    "When": 0,
                                    "Code": 0,
                                    "Msg": "Reboot initiated (HTTPS path caused disconnect/timeout)"
                                }],
                                "id": 1
                            }
                        except Exception as e:
                            last_error = str(e)
                            continue

        # If web interface fails, try CGMiner API as a last resort (software restart)
        try:
            import json
            payload = json.dumps({"command": "restart"})
            result = self._send_command(payload)
            return result
        except Exception as e:
            last_error = f"Web interface and CGMiner API both failed. Last error: {str(e)}"

        raise MinerError(f"Failed to restart miner: {last_error}")

    def switch_pool(self, pool_id: int) -> dict:
        """
        Switch to a different pool by its index/id.
        Example payload: {"command":"switchpool","parameter":"0"}
        """
        import json
        try:
            pid = int(pool_id)
        except Exception:
            raise MinerError("pool_id must be an integer")
        payload = json.dumps({"command": "switchpool", "parameter": str(pid)})
        return self._send_command(payload)
