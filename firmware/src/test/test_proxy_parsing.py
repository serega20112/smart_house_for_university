"""Checks the header parsing used by the firmware proxy.

The firmware separates the backend answer into status, content type and body
before handing it to the browser. This is the same algorithm expressed in Python
so it can be exercised against a real backend response.
"""

from __future__ import annotations

import sys


def header_boundary(data: bytes) -> int:
    """Return the offset of the empty line that ends the headers, or zero."""
    for i in range(len(data) - 3):
        if data[i : i + 4] == b"\r\n\r\n":
            return i
    return 0


def read_header_value(data: bytes, length: int, name: str) -> str | None:
    """Return a trimmed header value, matching the name without case."""
    target = name.lower().encode()
    offset = 0
    while offset + len(target) + 2 < length:
        if data[offset : offset + 2] == b"\r\n":
            offset += 2
            continue
        if data[offset : offset + len(target)].lower() == target and data[offset + len(target) : offset + len(target) + 1] == b":":
            cursor = offset + len(target) + 1
            while cursor < length and data[cursor : cursor + 1] == b" ":
                cursor += 1
            end = cursor
            while end < length and data[end : end + 1] not in (b"\r", b"\n"):
                end += 1
            return data[cursor:end].decode("utf-8", "replace")
        while offset < length and data[offset : offset + 1] not in (b"\r", b"\n"):
            offset += 1
    return None


def split_response(raw: bytes) -> tuple[int, str, bytes]:
    """Split a raw backend answer into status code, content type and body."""
    split = header_boundary(raw)
    if split == 0:
        raise ValueError("no header boundary")
    head = raw[:split].decode("utf-8", "replace")
    status = int(head.split()[1]) if len(head.split()) > 1 else 200
    content_type = read_header_value(raw, split, "content-type") or "application/json"
    length_header = read_header_value(raw, split, "content-length")
    body = raw[split + 4 :]
    if length_header is not None:
        body = body[: int(length_header)]
    return status, content_type, body


def main() -> int:
    raw = (
        b"HTTP/1.1 200 OK\r\n"
        b"date: Mon, 01 Jan 2026 00:00:00 GMT\r\n"
        b"server: uvicorn\r\n"
        b"content-length: 13\r\n"
        b"content-type: application/json\r\n"
        b"\r\n"
        b'{"ok":true}'
    )
    status, content_type, body = split_response(raw)
    assert status == 200, status
    assert content_type == "application/json", content_type
    assert body == b'{"ok":true}', body
    print("synthetic response parsed correctly")

    try:
        split_response(b"garbage without headers")
    except ValueError:
        print("malformed answer rejected correctly")
    else:
        print("FAIL: malformed answer was accepted")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
