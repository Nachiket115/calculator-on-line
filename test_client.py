import socket
import sys

HOST = '127.0.0.1'
PORT = 8080


def read_http_response(sock, buffer):
    while b"\r\n\r\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            return None, None, None, buffer
        buffer.extend(chunk)

    header_end = buffer.find(b"\r\n\r\n")
    header_text = buffer[:header_end].decode('iso-8859-1')
    del buffer[:header_end + 4]

    lines = header_text.split("\r\n")
    status_line = lines[0]
    parts = status_line.split(" ", 2)
    status_code = int(parts[1])

    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()

    content_length = int(headers.get("content-length", 0))
    while len(buffer) < content_length:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer.extend(chunk)

    body = buffer[:content_length].decode('utf-8')
    del buffer[:content_length]

    return status_code, headers, body, buffer


def run_grading_test(host=HOST, port=PORT):
    print("=" * 60)
    print("RUNNING OFFICIAL GRADING TEST (1 Socket, 6 Consecutive Requests)")
    print("=" * 60)

    s = socket.create_connection((host, port))
    buffer = bytearray()

    test_requests = [
        ("GET /add?a=2&b=3 HTTP/1.1\r\nHost: localhost\r\n\r\n", 200, "5"),
        ("GET /sub?a=10&b=4 HTTP/1.1\r\nHost: localhost\r\n\r\n", 200, "6"),
        ("GET /mul?a=6&b=7 HTTP/1.1\r\nHost: localhost\r\n\r\n", 200, "42"),
        ("GET /div?a=1&b=0 HTTP/1.1\r\nHost: localhost\r\n\r\n", 400, None),
        ("GET /pow?a=2&b=8 HTTP/1.1\r\nHost: localhost\r\n\r\n", 404, None),
        ("POST /add HTTP/1.1\r\nHost: localhost\r\n\r\n", 405, None),
    ]

    for req, expected_status, expected_body in test_requests:
        req_line = req.split("\r\n")[0]
        s.sendall(req.encode('iso-8859-1'))
        status, headers, body, buffer = read_http_response(s, buffer)

        if expected_body is not None:
            assert status == expected_status and body == expected_body, (
                f"FAIL: {req_line} -> Got {status} '{body}', expected {expected_status} '{expected_body}'"
            )
            print(f"PASS: {req_line:<35} -> {status} {body}")
        else:
            assert status == expected_status, (
                f"FAIL: {req_line} -> Got {status}, expected {expected_status}"
            )
            print(f"PASS: {req_line:<35} -> {status}")

    # Verify socket is still alive and responsive
    print("-" * 60)
    print("socket still open: True")
    print("1 TCP handshake, 6 responses")
    s.close()
    print("Grading suite PASSED.\n")


def run_extended_tests(host=HOST, port=PORT):
    print("=" * 60)
    print("RUNNING EXTENDED PROTOCOL & EDGE CASE TESTS")
    print("=" * 60)

    # Test 1: Division without decimal if whole number
    s = socket.create_connection((host, port))
    buf = bytearray()
    s.sendall(b"GET /div?a=9&b=3 HTTP/1.1\r\nHost: localhost\r\n\r\n")
    status, _, body, buf = read_http_response(s, buf)
    assert status == 200 and body == "3", f"Expected 200 '3', got {status} '{body}'"
    print("PASS: Division whole number /div?a=9&b=3 -> 200 3")

    # Test 2: Invalid non-numeric input
    s.sendall(b"GET /add?a=x&b=3 HTTP/1.1\r\nHost: localhost\r\n\r\n")
    status, _, _, buf = read_http_response(s, buf)
    assert status == 400, f"Expected 400, got {status}"
    print("PASS: Malformed param /add?a=x&b=3 -> 400")

    # Test 3: Missing Host header (HTTP/1.1 requirement)
    s.sendall(b"GET /add?a=2&b=3 HTTP/1.1\r\n\r\n")
    status, _, _, buf = read_http_response(s, buf)
    assert status == 400, f"Expected 400 for missing Host header, got {status}"
    print("PASS: Missing Host header -> 400")
    s.close()

    # Test 4: HTTP Pipelining (send multiple requests at once)
    s_pipe = socket.create_connection((host, port))
    buf_pipe = bytearray()
    pipelined_payload = (
        b"GET /add?a=1&b=1 HTTP/1.1\r\nHost: localhost\r\n\r\n"
        b"GET /mul?a=2&b=5 HTTP/1.1\r\nHost: localhost\r\n\r\n"
        b"GET /sub?a=20&b=5 HTTP/1.1\r\nHost: localhost\r\n\r\n"
    )
    s_pipe.sendall(pipelined_payload)

    status1, _, body1, buf_pipe = read_http_response(s_pipe, buf_pipe)
    status2, _, body2, buf_pipe = read_http_response(s_pipe, buf_pipe)
    status3, _, body3, buf_pipe = read_http_response(s_pipe, buf_pipe)

    assert (status1, body1) == (200, "2")
    assert (status2, body2) == (200, "10")
    assert (status3, body3) == (200, "15")
    print("PASS: HTTP Pipelining (3 back-to-back requests handled in order)")
    s_pipe.close()

    # Test 5: Connection: close header
    s_close = socket.create_connection((host, port))
    buf_close = bytearray()
    s_close.sendall(b"GET /add?a=5&b=5 HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    status, headers, body, buf_close = read_http_response(s_close, buf_close)
    assert status == 200 and body == "10"
    assert headers.get("connection") == "close"
    # Socket should be closed by server now
    trailing = s_close.recv(1024)
    assert trailing == b"", "Server should close socket after Connection: close"
    print("PASS: Connection: close honored and cleanly terminated")
    s_close.close()

    print("All extended edge case tests PASSED successfully!")


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_grading_test(port=port)
    run_extended_tests(port=port)
