import socket
import sys

HOST = '127.0.0.1'
PORT = 8080

VALID_ROUTES = {'/add', '/sub', '/mul', '/div'}


def parse_headers(header_text):
    lines = header_text.split("\r\n")
    request_line = lines[0]
    parts = request_line.split()
    
    if len(parts) != 3:
        return None, None, None, {}
    
    method, path, version = parts
    headers = {}
    
    for line in lines[1:]:
        if not line:
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip().lower()] = val.strip()
            
    return method, path, version, headers


def read_http_request(client_socket, buffer):
    while b"\r\n\r\n" not in buffer:
        chunk = client_socket.recv(4096)
        if not chunk:
            return None, buffer
        buffer.extend(chunk)

    header_end = buffer.find(b"\r\n\r\n")
    header_bytes = buffer[:header_end]
    del buffer[:header_end + 4]

    header_text = header_bytes.decode('iso-8859-1')
    method, path, version, headers = parse_headers(header_text)
    
    if method is None:
        return {"malformed": True}, buffer

    body = b""
    try:
        content_length = int(headers.get("content-length", 0))
    except ValueError:
        return {"malformed": True}, buffer

    while len(buffer) < content_length:
        chunk = client_socket.recv(4096)
        if not chunk:
            break
        buffer.extend(chunk)

    if content_length > 0:
        body = bytes(buffer[:content_length])
        del buffer[:content_length]

    request = {
        "method": method,
        "path": path,
        "version": version,
        "headers": headers,
        "body": body,
        "malformed": False
    }
    return request, buffer


def parse_query_params(query_string):
    params = {}
    if not query_string:
        return params
    for part in query_string.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            params[k] = v
    return params


def process_request(request):
    if request.get("malformed"):
        return 400, "Bad Request", "400 Bad Request"

    # HTTP/1.1 requires a Host header
    if "host" not in request["headers"]:
        return 400, "Bad Request", "400 Bad Request"

    raw_path = request["path"]
    if "?" in raw_path:
        endpoint, query_string = raw_path.split("?", 1)
    else:
        endpoint, query_string = raw_path, ""

    # Check if route exists
    if endpoint not in VALID_ROUTES:
        return 404, "Not Found", "404 Not Found"

    # Only GET is allowed for calculator routes
    if request["method"] != "GET":
        return 405, "Method Not Allowed", "405 Method Not Allowed"

    params = parse_query_params(query_string)
    if "a" not in params or "b" not in params:
        return 400, "Bad Request", "400 Bad Request"

    try:
        a = float(params["a"])
        b = float(params["b"])
    except ValueError:
        return 400, "Bad Request", "400 Bad Request"

    if endpoint == "/add":
        res = a + b
    elif endpoint == "/sub":
        res = a - b
    elif endpoint == "/mul":
        res = a * b
    elif endpoint == "/div":
        if b == 0:
            return 400, "Bad Request", "400 Bad Request"
        res = a / b
    else:
        return 404, "Not Found", "404 Not Found"

    # Format integers cleanly without trailing .0
    result_str = str(int(res)) if res.is_integer() else str(res)
    return 200, "OK", result_str


def handle_client(client_socket, client_address):
    print(f"Connected: {client_address}")
    buffer = bytearray()
    
    try:
        while True:
            request, buffer = read_http_request(client_socket, buffer)
            if request is None:
                break

            status_code, reason, body = process_request(request)
            print(f"[{client_address}] {request.get('method')} {request.get('path')} -> {status_code} {body}")

    except ConnectionResetError:
        pass
    except Exception as e:
        print(f"Error handling {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"Closed: {client_address}")


def run_server(host=HOST, port=PORT):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Server running on {host}:{port}")
        
        while True:
            client_socket, client_address = server_socket.accept()
            handle_client(client_socket, client_address)
            
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_socket.close()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port=port)
