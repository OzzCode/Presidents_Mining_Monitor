import pytest
import socket
from core.miner import MinerClient


# Edge Case: CGMiner API returns invalid JSON
class BadJSONSocket:
    def __init__(self, *args, **kwargs):
        self._data = b'invalid_json'

    def settimeout(self, timeout):
        pass

    def connect(self, addr):
        pass

    def sendall(self, data):
        pass

    def recv(self, bufsize):
        chunk, self._data = self._data, b''
        return chunk

    def close(self):
        pass


@pytest.fixture
def patch_bad_socket(monkeypatch):
    monkeypatch.setattr(socket, 'socket', lambda *args, **kwargs: BadJSONSocket())
    return None


def test_get_summary_invalid_json(patch_bad_socket):
    client = MinerClient('127.0.0.1')
    with pytest.raises(ValueError):
        client.get_summary()


# Edge Case: CGMiner API times out
class TimeoutSocket(BadJSONSocket):
    def connect(self, addr):
        raise socket.timeout()


@pytest.fixture
def patch_timeout_socket(monkeypatch):
    monkeypatch.setattr(socket, 'socket', lambda *args, **kwargs: TimeoutSocket())
    return None


def test_get_summary_timeout(patch_timeout_socket):
    client = MinerClient('127.0.0.1', timeout=0)
    with pytest.raises(socket.timeout):
        client.get_summary()
