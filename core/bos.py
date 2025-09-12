import requests


class BosRest:
    """
    Minimal client for Braiins OS (bos-public-api).

    Usage:
        bos = BosRest(ip, username, password)
        info = bos.details()
        bos.pause()
        bos.set_power_target(3200)
    """

    def __init__(self, ip: str, username: str, password: str, timeout: int = 5):
        if not ip:
            raise ValueError("ip is required")
        if not username:
            raise ValueError("username is required")
        if password is None:
            password = ""
        self.base = f"http://{ip}/api/v1"
        self.timeout = timeout
        r = requests.post(
            f"{self.base}/auth/login",
            json={"username": username, "password": password},
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json() or {}
        token = data.get("token")
        if not token:
            raise RuntimeError("BOS login did not return a token")
        self.token = token
        self.h = {"Authorization": self.token}

    def details(self):
        r = requests.get(f"{self.base}/miner/details", headers=self.h, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def pause(self):
        r = requests.put(f"{self.base}/actions/pause", headers=self.h, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def set_power_target(self, watts: int):
        try:
            w = int(watts)
        except Exception:
            raise ValueError("watts must be an integer")
        r = requests.put(
            f"{self.base}/performance/power-target",
            headers=self.h,
            json={"watt": w},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()
