"""
ssh_honeypot.py
Honeypot SSH de baja interacción basado en paramiko.

Paramiko se encarga del handshake SSH real (intercambio de claves, cifrado
del transporte), por lo que la conexión es indistinguible de un servidor
SSH de verdad hasta la fase de autenticación. Aquí interceptamos cada
intento de usuario/contraseña, lo registramos y SIEMPRE devolvemos
"autenticación fallida": el atacante nunca obtiene una shell real.
"""

import socket
import threading
from pathlib import Path

import paramiko

from . import geoip, logger

HOST_KEY_PATH = Path(__file__).resolve().parent.parent / "data" / "host_key.pem"


def _get_or_create_host_key() -> paramiko.RSAKey:
    HOST_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if HOST_KEY_PATH.exists():
        return paramiko.RSAKey(filename=str(HOST_KEY_PATH))
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(str(HOST_KEY_PATH))
    return key


class HoneypotSSHServer(paramiko.ServerInterface):
    def __init__(self, client_ip: str, client_port: int):
        self.client_ip = client_ip
        self.client_port = client_port
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        geo = geoip.lookup(self.client_ip)
        logger.log_attempt(
            protocol="ssh",
            src_ip=self.client_ip,
            src_port=self.client_port,
            username=username,
            password=password,
            country=geo["country"],
            city=geo["city"],
        )
        # Nunca se concede acceso: solo nos interesa registrar el intento.
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        geo = geoip.lookup(self.client_ip)
        logger.log_attempt(
            protocol="ssh-pubkey",
            src_ip=self.client_ip,
            src_port=self.client_port,
            username=username,
            password=f"<clave_publica:{key.get_name()}>",
            country=geo["country"],
            city=geo["city"],
        )
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password,publickey"


def _handle_connection(client_sock: socket.socket, addr, host_key: paramiko.RSAKey):
    ip, port = addr
    transport = paramiko.Transport(client_sock)
    transport.add_server_key(host_key)
    transport.local_version = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5"

    server = HoneypotSSHServer(ip, port)
    try:
        transport.start_server(server=server)
        chan = transport.accept(20)
        if chan is not None:
            chan.close()
    except Exception:
        pass
    finally:
        try:
            transport.close()
        except Exception:
            pass


def serve(host: str = "0.0.0.0", port: int = 2222):
    """
    Por defecto escucha en el puerto 2222 (no requiere privilegios root).
    Para exponerlo como el puerto SSH real (22) usa un redirect con
    iptables/nftables, ver README.
    """
    host_key = _get_or_create_host_key()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(100)
    print(f"[ssh-honeypot] escuchando en {host}:{port}")

    def _accept_loop():
        while True:
            try:
                client_sock, addr = sock.accept()
            except OSError:
                break
            threading.Thread(
                target=_handle_connection,
                args=(client_sock, addr, host_key),
                daemon=True,
            ).start()

    thread = threading.Thread(target=_accept_loop, daemon=True)
    thread.start()
    return sock
