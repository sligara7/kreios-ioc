"""Minimal Prodigy Remote In client

Provides a tiny, testable socket client implementing the ASCII request/response framing
used by SpecsLab Prodigy Remote In.

Requests:  ?<id> Command [key:val ...]\n
Responses: !<id> OK[: key:val ...]\n or !<id> Error: <code> [Reason]\n
This client is intentionally small and synchronous. It is suitable to be wrapped by a
proxy service that holds the single connection.
"""

import socket
import threading
import time
import re
import itertools
from typing import Optional, Dict, Tuple, Any


class ProdigyProtocolError(Exception):
    pass


class ProdigyClient:
    def __init__(self, host: str, port: int = 7010, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self._id_counter = itertools.count(1)
        self._recv_lock = threading.Lock()
        self._send_lock = threading.Lock()

    def connect(self) -> None:
        if self.sock:
            return
        s = socket.create_connection((self.host, self.port), timeout=self.timeout)
        s.settimeout(self.timeout)
        self.sock = s

    def disconnect(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _next_id(self) -> str:
        # 4 hex digits
        n = next(self._id_counter)
        return f"{n:04X}"  # uppercase hex, zero-padded

    @staticmethod
    def _format_params(params: Optional[Dict[str, Any]]) -> str:
        if not params:
            return ""
        parts = []
        for k, v in params.items():
            if isinstance(v, str):
                # escape double quotes
                safe = v.replace('"', '\\"')
                parts.append(f'{k}:"{safe}"')
            else:
                parts.append(f"{k}:{v}")
        return " " + " ".join(parts)

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None, expect_response: bool = True) -> Dict[str, Any]:
        """Send a command and wait for response parsed into a dict.

        Returns a dict with keys: success(bool), data(dict) if success, error(tuple(code, message)) if not.
        """
        if not self.sock:
            raise ProdigyProtocolError("Not connected")

        req_id = self._next_id()
        payload = f"?{req_id} {command}{self._format_params(params)}\n"

        with self._send_lock:
            self.sock.sendall(payload.encode("utf-8"))

        if not expect_response:
            return {"success": True, "data": {}}

        # receive response line
        with self._recv_lock:
            # read until newline
            buf = bytearray()
            start = time.time()
            while True:
                if time.time() - start > self.timeout:
                    raise ProdigyProtocolError("Response timeout")
                try:
                    chunk = self.sock.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    raise ProdigyProtocolError("Connection closed by peer")
                buf.extend(chunk)
                if b"\n" in buf:
                    break
            line, _, _ = buf.partition(b"\n")
            text = line.decode("utf-8", errors="replace").strip()

        resp = self._parse_response(text)
        if resp[0] != req_id:
            # In a real client we would need to buffer or match multiple replies; keep it simple here.
            raise ProdigyProtocolError(f"Mismatched response id: expected {req_id}, got {resp[0]}")

        status = resp[1]
        payload = resp[2]
        if status == "OK":
            return {"success": True, "data": payload}
        else:
            # status "Error"
            return {"success": False, "error": payload}

    _resp_re = re.compile(r"^!([0-9A-Fa-f]{4})\s+(OK|Error):?(?:\s*(.*))?$")

    @classmethod
    def _parse_response(cls, text: str) -> Tuple[str, str, Dict[str, Any]]:
        # returns (id, status, payload_dict_or_error)
        m = cls._resp_re.match(text)
        if not m:
            raise ProdigyProtocolError(f"Malformed response: {text}")
        req_id = m.group(1).upper()
        status = m.group(2)
        rest = m.group(3) or ""

        if status == "OK":
            # rest may be empty or like: Key:Value Key2:Value2 or Data:[v1,v2,...]
            if not rest:
                return req_id, status, {}
            # parse key:value pairs; naive parsing that supports quoted strings and bracketed lists
            payload = {}
            # split respecting quotes
            tokens = cls._tokenize(rest)
            # tokens are like ['Key:Value', 'Key2:"Some value"'] or 'Data:[1,2,3]'
            for tok in tokens:
                if ":" not in tok:
                    continue
                k, v = tok.split(":", 1)
                k = k.strip()
                v = v.strip()
                if v.startswith('"') and v.endswith('"'):
                    # quoted string
                    payload[k] = v[1:-1].replace('\\"', '"')
                elif v.startswith("[") and v.endswith("]"):
                    # list of numbers or strings (simple)
                    inner = v[1:-1].strip()
                    if not inner:
                        payload[k] = []
                    else:
                        items = [it.strip() for it in inner.split(",")]
                        parsed = []
                        for it in items:
                            if it.startswith('"') and it.endswith('"'):
                                parsed.append(it[1:-1].replace('\\"', '"'))
                            else:
                                try:
                                    if '.' in it:
                                        parsed.append(float(it))
                                    else:
                                        parsed.append(int(it))
                                except ValueError:
                                    parsed.append(it)
                        payload[k] = parsed
                else:
                    # try number
                    try:
                        if '.' in v:
                            payload[k] = float(v)
                        else:
                            payload[k] = int(v)
                    except ValueError:
                        payload[k] = v
            return req_id, status, payload
        else:
            # Error: rest starts with code and optional message
            rest = rest.strip()
            if not rest:
                return req_id, status, (None, "")
            parts = rest.split(" ", 1)
            try:
                code = int(parts[0])
                msg = parts[1] if len(parts) > 1 else ""
            except ValueError:
                code = None
                msg = rest
            return req_id, status, (code, msg)

    @staticmethod
    def _tokenize(s: str):
        # splits on spaces but keeps quoted strings and bracketed lists intact
        tokens = []
        cur = []
        in_quote = False
        in_bracket = 0
        i = 0
        while i < len(s):
            ch = s[i]
            if ch == '"' and in_bracket == 0:
                in_quote = not in_quote
                cur.append(ch)
            elif ch == '[' and not in_quote:
                in_bracket += 1
                cur.append(ch)
            elif ch == ']' and not in_quote:
                in_bracket -= 1
                cur.append(ch)
            elif ch == ' ' and not in_quote and in_bracket == 0:
                if cur:
                    tokens.append(''.join(cur))
                    cur = []
            else:
                cur.append(ch)
            i += 1
        if cur:
            tokens.append(''.join(cur))
        return tokens


if __name__ == '__main__':
    # small demo when run directly: connect and send a Connect command
    import sys
    if len(sys.argv) < 2:
        print("Usage: prodigy_client.py <host> [port]")
        sys.exit(2)
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 7010
    c = ProdigyClient(host, port)
    try:
        c.connect()
        print("Connected")
        r = c.send_command("Connect")
        print(r)
    finally:
        c.disconnect()
