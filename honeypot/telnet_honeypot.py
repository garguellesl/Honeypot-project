"""
telnet_honeypot.py
Honeypot Telnet de baja interacción.

Simula el banner de login de un router/NVR doméstico, captura las
credenciales que el atacante introduce y cierra la conexión. Nunca concede
acceso real ni ejecuta nada de lo que envía el cliente: solo lee texto.
"""

import socketserver
import threading

from . import geoip, logger

BANNER = b"\r\nUbuntu 20.04.3 LTS\r\n"
LOGIN_PROMPT = b"login: "
PASSWORD_PROMPT = b"Password: "


class TelnetHandler(socketserver.BaseRequestHandler):
    def handle(self):
        ip, port = self.client_address
        try:
            self.request.settimeout(15)
            self.request.sendall(BANNER)
            self.request.sendall(LOGIN_PROMPT)
            username = self._read_line()

            self.request.sendall(PASSWORD_PROMPT)
            password = self._read_line()

            geo = geoip.lookup(ip)
            logger.log_attempt(
                protocol="telnet",
                src_ip=ip,
                src_port=port,
                username=username,
                password=password,
                country=geo["country"],
                city=geo["city"],
            )

            # Simula un login fallido y cierra. No se concede shell jamás.
            self.request.sendall(b"\r\nLogin incorrect\r\n")
        except Exception:
            pass
        finally:
            self.request.close()

    def _read_line(self, max_len: int = 64) -> str:
        data = bytearray()
        while len(data) < max_len:
            chunk = self.request.recv(1)
            if not chunk or chunk in (b"\r", b"\n"):
                break
            data += chunk
        return data.decode("utf-8", errors="replace").strip()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(host: str = "0.0.0.0", port: int = 2323):
    """
    Por defecto escucha en el puerto 2323 (no requiere privilegios root).
    Para exponerlo como el puerto Telnet real (23) usa un redirect con
    iptables/nftables en el Raspberry Pi, ver README.
    """
    server = ThreadedTCPServer((host, port), TelnetHandler)
    print(f"[telnet-honeypot] escuchando en {host}:{port}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
