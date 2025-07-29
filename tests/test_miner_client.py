import pytest
import socket
import json
from core.miner import MinerClient


class DummySocket:
    def __init__(self, *args, **kwargs):
        self._data = b''

    def settimeout(self, timeout):
        pass

    def connect(self, addr):
        pass

    def sendall(self, data):
        # simulate CGMiner JSON response
        self._data = b'{"test": 123}'

    def recv(self, bufsize):
        chunk = self._data
        self._data = b''
        return chunk

    def close(self):
        pass


@pytest.fixture(autouse=True)
def patch_socket(monkeypatch):
    monkeypatch.setattr(socket, 'socket', lambda *args, **kwargs: DummySocket())
    return None


def test_get_summary_parses_json():
    client = MinerClient('127.0.0.1')
    result = client.get_summary()
    assert result == {"test": 123}
