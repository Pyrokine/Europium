import socket


def is_port_in_use(port: int, host: str = '127.0.0.1') -> bool:
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            s.connect((host, port))
            s.close()
            return True
        except socket.error:
            s.close()
            return False
