import socket
import sys

HOST = '127.0.0.1'
PORT = 8080

def handle_client(client_socket, client_address):
    print(f"Connected: {client_address}")
    
    try:
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            
            # Temporary echo/log 
            print(f"Received {len(data)} bytes from {client_address}")
            
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
