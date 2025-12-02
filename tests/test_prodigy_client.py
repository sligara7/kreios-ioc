import socket
import threading
import time
import pytest
from tools.prodigy_client import ProdigyClient, ProdigyProtocolError


class MockProdigyServer(threading.Thread):
    def __init__(self, host='127.0.0.1', port=7010, response_map=None):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.response_map = response_map or {}
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(1)
        self.running = True

    def run(self):
        while self.running:
            try:
                conn, addr = self._sock.accept()
            except OSError:
                break
            with conn:
                conn.settimeout(1.0)
                try:
                    data = b""
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                        if b"\n" in data:
                            break
                    text = data.decode('utf-8').strip()
                    # expect ?<id> Command ...
                    if not text.startswith('?'):
                        # ignore
                        continue
                    # echo map
                    parts = text.split(None, 2)
                    if len(parts) >= 2:
                        req_id = parts[0][1:]
                        cmd = parts[1]
                    else:
                        req_id = '0000'
                        cmd = ''
                    # default OK
                    resp = self.response_map.get(cmd)
                    if resp is None:
                        # simple OK
                        out = f"!{req_id} OK\n"
                    else:
                        out = f"!{req_id} {resp}\n"
                    conn.sendall(out.encode('utf-8'))
                except socket.timeout:
                    continue

    def stop(self):
        self.running = False
        try:
            self._sock.close()
        except Exception:
            pass


def test_connect_and_simple_ok(tmp_path):
    server = MockProdigyServer(port=7011)
    server.start()
    try:
        c = ProdigyClient('127.0.0.1', port=7011, timeout=2.0)
        c.connect()
        res = c.send_command('Connect')
        assert res['success'] is True
        assert res['data'] == {}
    finally:
        c.disconnect()
        server.stop()


def test_ok_with_params():
    # prepare server to respond with parameters
    resp_map = {'GetAcquisitionStatus': 'OK: ControllerState:running NumberOfAcquiredPoints:12'}
    server = MockProdigyServer(port=7012, response_map=resp_map)
    server.start()
    try:
        c = ProdigyClient('127.0.0.1', port=7012, timeout=2.0)
        c.connect()
        r = c.send_command('GetAcquisitionStatus')
        assert r['success'] is True
        assert r['data']['ControllerState'] == 'running'
        assert r['data']['NumberOfAcquiredPoints'] == 12
    finally:
        c.disconnect()
        server.stop()


def test_error_response():
    resp_map = {'ValidateSpectrum': 'Error: 202 Validation failed.'}
    server = MockProdigyServer(port=7013, response_map=resp_map)
    server.start()
    try:
        c = ProdigyClient('127.0.0.1', port=7013, timeout=2.0)
        c.connect()
        r = c.send_command('ValidateSpectrum')
        assert r['success'] is False
        assert isinstance(r['error'], tuple)
        assert r['error'][0] == 202
    finally:
        c.disconnect()
        server.stop()
